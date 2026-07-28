"""Local-image input preparation and OCR fallback for OpenAI-compatible models."""

from __future__ import annotations

import base64
import io
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


_IMAGE_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
)
_NATIVE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
_PATH_PATTERN = re.compile(
    r"""(?:
        (?P<quote>["'])(?P<quoted>[^"'\n]+?\.(?:png|jpe?g|gif|webp|bmp|tiff?))(?P=quote)
        |
        (?P<plain>[^\s"'<>|]+?\.(?:png|jpe?g|gif|webp|bmp|tiff?))
    )""",
    re.IGNORECASE | re.VERBOSE,
)
_VISUAL_FOLLOWUP_PATTERN = re.compile(
    r"(?:ảnh|hình|tấm\s+hình|image|picture|photo|screenshot|visual|pixel)",
    re.IGNORECASE,
)


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int((os.getenv(name) or str(default)).strip())
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def _vision_enabled() -> bool:
    value = (os.getenv("PKS_VISION", "auto") or "auto").strip().lower()
    return value not in {"0", "false", "off", "no", "disabled"}


def _normalize_user_path(raw: str) -> Path:
    value = raw.strip().strip("()[]{}<>,;")
    if value.lower().startswith(("http://", "https://", "data:")):
        raise ValueError("remote URLs are not local image paths")

    # Windows Explorer paths into WSL:
    # \\wsl.localhost\distro\home\user\x.png and \\wsl$\distro\...
    if re.match(r"^\\\\+(?:wsl\.localhost|wsl\$)\\", value, re.IGNORECASE):
        parts = [part for part in value.lstrip("\\").split("\\") if part]
        if len(parts) < 3:
            raise ValueError("invalid WSL path")
        value = "/" + "/".join(parts[2:])
    elif re.match(r"^[A-Za-z]:\\", value):
        drive = value[0].lower()
        value = f"/mnt/{drive}/" + value[3:].replace("\\", "/")

    return Path(os.path.expanduser(value)).resolve(strict=True)


def find_local_image_paths(text: str) -> tuple[Path, ...]:
    """Return existing local image paths explicitly present in operator text."""
    found: list[Path] = []
    seen: set[Path] = set()
    for match in _PATH_PATTERN.finditer(text or ""):
        raw = match.group("quoted") or match.group("plain") or ""
        try:
            path = _normalize_user_path(raw)
        except (OSError, ValueError):
            continue
        if path.suffix.lower() not in _IMAGE_EXTENSIONS or not path.is_file():
            continue
        if path not in seen:
            seen.add(path)
            found.append(path)
    return tuple(found)


def _image_dimensions(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image

        with Image.open(path) as image:
            return image.size
    except Exception:
        return (0, 0)


def _provider_image_bytes(path: Path) -> tuple[bytes, str]:
    suffix = path.suffix.lower()
    if suffix in _NATIVE_MIME:
        return path.read_bytes(), _NATIVE_MIME[suffix]

    # OpenAI-compatible vision endpoints are inconsistent for BMP/TIFF. Convert
    # those formats in memory so no temporary artifact or duplicate file is made.
    from PIL import Image

    output = io.BytesIO()
    with Image.open(path) as image:
        image.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue(), "image/png"


@dataclass(frozen=True)
class PreparedImage:
    path: Path
    data_url: str


@dataclass(frozen=True)
class PreparedVisionInput:
    """A model-ready multimodal turn plus enough metadata for OCR fallback."""

    original_text: str
    model_input: str | list[dict[str, Any]]
    images: tuple[PreparedImage, ...] = ()

    @property
    def has_images(self) -> bool:
        return bool(self.images)

    def ocr_fallback_input(self) -> str:
        if not self.images:
            return self.original_text

        command = shutil.which("pks-ocr")
        timeout = _env_int("PKS_OCR_TIMEOUT", 60, 5, 300)
        output_max = _env_int("PKS_TOOL_OUTPUT_MAX", 20_000, 800, 200_000)
        sections = [
            self.original_text,
            "",
            "[PKS vision fallback: the active model/provider rejected image input. "
            "Use the OCR evidence below and the original local paths.]",
        ]
        for image in self.images:
            sections.extend(["", f"Image: {image.path}"])
            if not command:
                sections.append(
                    "OCR unavailable: `pks-ocr` is not installed. Use an available "
                    "image/OCR tool on this path."
                )
                continue
            try:
                completed = subprocess.run(
                    [command, str(image.path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                combined = "\n".join(
                    part.strip()
                    for part in (completed.stdout, completed.stderr)
                    if part and part.strip()
                )
                if len(combined) > output_max:
                    combined = combined[:output_max] + "\n... OCR OUTPUT TRUNCATED ..."
                sections.append(combined or f"OCR produced no text (exit {completed.returncode}).")
            except subprocess.TimeoutExpired:
                sections.append(f"OCR timed out after {timeout}s.")
            except OSError as exc:
                sections.append(f"OCR failed: {exc}")
        return "\n".join(sections)


def prepare_vision_input(
    text: str,
    recent_paths: Iterable[Path] = (),
) -> PreparedVisionInput:
    """Attach explicit images, or the latest image for a visual follow-up."""
    if not _vision_enabled():
        return PreparedVisionInput(text, text)

    max_images = _env_int("PKS_IMAGE_MAX_COUNT", 4, 1, 12)
    max_each = _env_int("PKS_IMAGE_MAX_BYTES", 10_000_000, 64_000, 50_000_000)
    max_total = _env_int("PKS_IMAGE_TOTAL_MAX_BYTES", 20_000_000, max_each, 100_000_000)
    max_pixels = _env_int("PKS_IMAGE_MAX_PIXELS", 40_000_000, 1_000_000, 200_000_000)

    paths = list(find_local_image_paths(text))
    inferred = False
    if not paths and _VISUAL_FOLLOWUP_PATTERN.search(text or ""):
        seen: set[Path] = set()
        for candidate in recent_paths:
            try:
                path = Path(candidate).resolve(strict=True)
            except (OSError, ValueError):
                continue
            if (
                path not in seen
                and path.is_file()
                and path.suffix.lower() in _IMAGE_EXTENSIONS
            ):
                seen.add(path)
                paths.append(path)
        inferred = bool(paths)

    prepared: list[PreparedImage] = []
    total = 0
    for path in paths[:max_images]:
        try:
            size = path.stat().st_size
            width, height = _image_dimensions(path)
            if size > max_each or (width and height and width * height > max_pixels):
                continue
            raw, mime = _provider_image_bytes(path)
            if len(raw) > max_each or total + len(raw) > max_total:
                continue
        except (OSError, ValueError):
            continue
        total += len(raw)
        encoded = base64.b64encode(raw).decode("ascii")
        prepared.append(
            PreparedImage(path=path, data_url=f"data:{mime};base64,{encoded}")
        )

    if not prepared:
        return PreparedVisionInput(text, text)

    content: list[dict[str, Any]] = [{"type": "input_text", "text": text}]
    if inferred:
        content.append(
            {
                "type": "input_text",
                "text": "[PKS attached the most recent local image: "
                + ", ".join(str(image.path) for image in prepared)
                + "]",
            }
        )
    for image in prepared:
        content.append(
            {
                "type": "input_image",
                "image_url": image.data_url,
                "detail": "auto",
            }
        )
    return PreparedVisionInput(
        original_text=text,
        model_input=[{"role": "user", "content": content}],
        images=tuple(prepared),
    )


def _exception_chain(exc: BaseException) -> Iterable[BaseException]:
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def is_vision_rejection(exc: BaseException) -> bool:
    """Return true for provider/schema errors where dropping images may recover."""
    statuses: set[int] = set()
    text_parts: list[str] = []
    for item in _exception_chain(exc):
        text_parts.append(str(item))
        response = getattr(item, "response", None)
        status = getattr(response, "status_code", None)
        if isinstance(status, int):
            statuses.add(status)
        try:
            text_parts.append(str(response.text))
        except Exception:
            pass
        details = getattr(item, "details", None)
        if details:
            text_parts.append(str(details))

    combined = " ".join(text_parts).lower()
    keywords = (
        "input_image",
        "image_url",
        "image input",
        "image content",
        "multimodal",
        "vision",
        "only text",
        "unsupported content type",
    )
    if any(keyword in combined for keyword in keywords):
        return True
    # Callers only invoke this for a request that actually contains images.
    # Some OpenAI-compatible gateways return only a generic 400/422 here.
    return bool(statuses.intersection({400, 413, 415, 422}))


def input_has_images(value: Any) -> bool:
    """Return whether a Runner input/message contains an image content part."""
    items = value if isinstance(value, list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        if any(
            isinstance(part, dict)
            and part.get("type") in {"input_image", "image_url"}
            for part in content
        ):
            return True
    return False


def _content_has_data_url(content: Any, urls: set[str]) -> bool:
    if not isinstance(content, list):
        return False
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get("type") == "input_image" and part.get("image_url") in urls:
            return True
        image_url = part.get("image_url")
        if (
            part.get("type") == "image_url"
            and isinstance(image_url, dict)
            and image_url.get("url") in urls
        ):
            return True
    return False


def _history_lists(agent: Any) -> tuple[list[dict[str, Any]], ...]:
    histories: list[list[dict[str, Any]]] = []
    model = getattr(agent, "model", None)
    history = getattr(model, "message_history", None)
    if isinstance(history, list):
        histories.append(history)
    try:
        from pks.sdk.agents.simple_agent_manager import AGENT_MANAGER

        managed = AGENT_MANAGER.get_message_history(getattr(agent, "name", ""))
        if isinstance(managed, list) and all(managed is not item for item in histories):
            histories.append(managed)
    except Exception:
        pass
    return tuple(histories)


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(
        str(part.get("text", ""))
        for part in content
        if isinstance(part, dict) and part.get("text")
    )


def _recent_images_from_agent(agent: Any, limit: int = 4) -> tuple[Path, ...]:
    found: list[Path] = []
    seen: set[Path] = set()
    for history in _history_lists(agent):
        for message in reversed(history[-24:]):
            for path in reversed(find_local_image_paths(_message_text(message))):
                if path not in seen:
                    seen.add(path)
                    found.append(path)
                    if len(found) >= limit:
                        return tuple(found)
    return tuple(found)


def remember_recent_agent_images(owner_agent: Any, source_agent: Any) -> None:
    """Remember specialist image artifacts for a later Root visual follow-up."""
    images = _recent_images_from_agent(source_agent)
    if images:
        setattr(owner_agent, "_pks_recent_images", images)


def prepare_agent_vision_input(text: str, agent: Any) -> PreparedVisionInput:
    """Prepare a turn using explicit paths or recent artifacts from this workflow."""
    recent = getattr(agent, "_pks_recent_images", ())
    if not recent:
        recent = _recent_images_from_agent(agent)
    if not recent and os.getenv("PKS_TUI_MODE", "").lower() != "true":
        try:
            from pks.sdk.agents.simple_agent_manager import AGENT_MANAGER

            shared = AGENT_MANAGER.get_shared_context_injection()
            recent = tuple(reversed(find_local_image_paths(shared)))
        except Exception:
            recent = ()
    return prepare_vision_input(text, recent)


def _sync_parallel_history(agent: Any) -> None:
    model = getattr(agent, "model", None)
    history = getattr(model, "message_history", None)
    agent_id = getattr(model, "agent_id", None)
    if not isinstance(history, list) or not agent_id:
        return
    try:
        from pks.sdk.agents.parallel_isolation import PARALLEL_ISOLATION

        if PARALLEL_ISOLATION.is_parallel_mode():
            PARALLEL_ISOLATION.replace_isolated_history(agent_id, history)
    except Exception:
        pass


def remove_pending_vision_history(agent: Any, prepared: PreparedVisionInput) -> None:
    """Remove the failed image-bearing user turn before retrying with OCR."""
    urls = {image.data_url for image in prepared.images}
    for history in _history_lists(agent):
        for index in range(len(history) - 1, -1, -1):
            message = history[index]
            if message.get("role") == "user" and _content_has_data_url(
                message.get("content"), urls
            ):
                history.pop(index)
                break
    _sync_parallel_history(agent)


def compact_vision_history(agent: Any, prepared: PreparedVisionInput) -> None:
    """Replace base64 image history with compact local references after the turn."""
    path_by_url = {image.data_url: str(image.path) for image in prepared.images}
    urls = set(path_by_url)
    for history in _history_lists(agent):
        for message in history:
            content = message.get("content")
            if message.get("role") != "user" or not _content_has_data_url(content, urls):
                continue
            compacted: list[dict[str, str]] = []
            referenced: list[str] = []
            text_type = "input_text" if any(
                isinstance(part, dict)
                and part.get("type") in {"input_text", "input_image"}
                for part in content
            ) else "text"
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") in {"text", "input_text"}:
                    compacted.append(
                        {"type": text_type, "text": str(part.get("text", ""))}
                    )
                    continue
                image_url = part.get("image_url")
                url = (
                    image_url.get("url")
                    if isinstance(image_url, dict)
                    else image_url
                )
                if url in path_by_url:
                    referenced.append(path_by_url[url])
            if referenced:
                compacted.append(
                    {
                        "type": text_type,
                        "text": "[PKS local image reference: "
                        + ", ".join(referenced)
                        + ". Re-open or OCR the file if pixel evidence is needed again.]",
                    }
                )
            message["content"] = compacted
    _sync_parallel_history(agent)
