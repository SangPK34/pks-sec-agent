from __future__ import annotations

import base64
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from pks.util.vision import (
    PreparedImage,
    PreparedVisionInput,
    compact_vision_history,
    find_local_image_paths,
    find_tool_image_paths,
    input_has_images,
    is_vision_rejection,
    prepare_image_artifacts,
    prepare_agent_vision_input,
    prepare_vision_input,
    remove_pending_vision_history,
)
from pks.sdk.agents.run_to_jsonl import _sanitize_messages_for_log


def _write_png(path: Path) -> None:
    image_format = "JPEG" if path.suffix.lower() in {".jpg", ".jpeg"} else "PNG"
    Image.new("RGB", (8, 6), "white").save(path, image_format)


def test_prepare_local_image_as_multimodal_input(tmp_path: Path) -> None:
    image_path = tmp_path / "flag image.png"
    _write_png(image_path)

    prepared = prepare_vision_input(f'đọc flag trong "{image_path}"')

    assert prepared.has_images
    assert input_has_images(prepared.model_input)
    message = prepared.model_input[0]
    assert message["role"] == "user"
    assert message["content"][0] == {
        "type": "input_text",
        "text": f'đọc flag trong "{image_path}"',
    }
    image_part = message["content"][1]
    assert image_part["type"] == "input_image"
    assert image_part["detail"] == "auto"
    assert image_part["image_url"].startswith("data:image/png;base64,")
    base64.b64decode(image_part["image_url"].split(",", 1)[1], validate=True)


def test_agent_path_input_stays_text_until_model_selects_view(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "flag.png"
    _write_png(image_path)
    text = f"ghi nhớ path này, chưa cần xem: {image_path}"

    prepared = prepare_agent_vision_input(text, SimpleNamespace())

    assert prepared.model_input == text
    assert not prepared.has_images


def test_prepare_vision_can_be_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_path = tmp_path / "flag.png"
    _write_png(image_path)
    text = f"inspect {image_path}"
    monkeypatch.setenv("PKS_VISION", "off")

    prepared = prepare_vision_input(text)

    assert prepared.model_input == text
    assert not prepared.has_images


def test_prepare_tool_artifact_does_not_depend_on_user_wording(tmp_path: Path) -> None:
    latest_image = tmp_path / "fixed.jpg"
    _write_png(latest_image)

    prepared = prepare_image_artifacts(
        [latest_image],
        "[PKS attached an artifact produced by a tool.]",
    )

    assert prepared.has_images
    assert prepared.images[0].path == latest_image.resolve()
    assert input_has_images(prepared.model_input)


def test_find_local_image_paths_accepts_wsl_explorer_path() -> None:
    image_path = Path.home() / ".pks-vision-path-test.png"
    try:
        _write_png(image_path)
        windows_path = (
            r"\\wsl.localhost\kali-linux"
            + str(image_path).replace("/", "\\")
        )

        assert find_local_image_paths(f'check "{windows_path}"') == (
            image_path.resolve(),
        )
    finally:
        image_path.unlink(missing_ok=True)


@pytest.mark.parametrize(
    ("image_format", "tool_description"),
    [
        ("JPEG", "JPEG image data, JFIF standard 1.01, 20x10"),
        ("PNG", "PNG image data, 20 x 10, 8-bit/color RGB"),
        ("GIF", "GIF image data, version 87a, 20 x 10"),
        ("TIFF", "TIFF image data, little-endian, width=20, height=10"),
        ("BMP", "PC bitmap, Windows 3.x format, 20 x 10 x 24"),
        ("WEBP", "RIFF (little-endian) data, Web/P image, VP8 encoding, 20x10"),
    ],
)
def test_tool_image_detection_accepts_extensionless_file(
    tmp_path: Path,
    image_format: str,
    tool_description: str,
) -> None:
    image_path = tmp_path / "file"
    Image.new("RGB", (20, 10), "white").save(image_path, image_format)

    paths = find_tool_image_paths(
        f"file: {tool_description}",
        (tmp_path,),
    )
    prepared = prepare_image_artifacts(paths)

    assert paths == (image_path.resolve(),)
    assert prepared.has_images
    assert prepared.images[0].data_url.startswith("data:image/png;base64,")


def test_history_cleanup_and_compaction_do_not_keep_base64(tmp_path: Path) -> None:
    image_path = tmp_path / "flag.png"
    _write_png(image_path)
    data_url = "data:image/png;base64,AAAA"
    prepared = PreparedVisionInput(
        original_text="inspect",
        model_input=[],
        images=(PreparedImage(image_path, data_url),),
    )
    message = {
        "role": "user",
        "content": [
            {"type": "text", "text": "inspect"},
            {
                "type": "image_url",
                "image_url": {"url": data_url, "detail": "auto"},
            },
        ],
    }
    agent = SimpleNamespace(
        name="vision-test-agent",
        model=SimpleNamespace(message_history=[message]),
    )

    compact_vision_history(agent, prepared)

    compacted = agent.model.message_history[0]["content"]
    assert data_url not in str(compacted)
    assert str(image_path) in str(compacted)

    agent.model.message_history[:] = [message.copy()]
    agent.model.message_history[0]["content"] = [
        {"type": "image_url", "image_url": {"url": data_url}}
    ]
    remove_pending_vision_history(agent, prepared)
    assert agent.model.message_history == []


def test_vision_rejection_accepts_generic_gateway_client_error() -> None:
    assert is_vision_rejection(ValueError("input_image is not supported"))

    unrelated = RuntimeError("400 Bad Request: invalid tool schema")
    unrelated.response = SimpleNamespace(  # type: ignore[attr-defined]
        status_code=400,
        text="invalid tool schema",
    )
    assert is_vision_rejection(unrelated)

    unsupported_media = RuntimeError("Unsupported Media Type")
    unsupported_media.response = SimpleNamespace(  # type: ignore[attr-defined]
        status_code=415,
        text="",
    )
    assert is_vision_rejection(unsupported_media)


def test_ocr_fallback_is_lazy_and_capped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_path = tmp_path / "flag.png"
    _write_png(image_path)
    prepared = PreparedVisionInput(
        original_text="inspect",
        model_input=[],
        images=(PreparedImage(image_path, "data:image/png;base64,AAAA"),),
    )
    monkeypatch.setattr("pks.util.vision.shutil.which", lambda _name: "/usr/bin/pks-ocr")
    monkeypatch.setenv("PKS_TOOL_OUTPUT_MAX", "800")
    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return SimpleNamespace(stdout="A" * 1_000, stderr="", returncode=0)

    monkeypatch.setattr("pks.util.vision.subprocess.run", fake_run)

    fallback = prepared.ocr_fallback_input()

    assert calls == [["/usr/bin/pks-ocr", str(image_path)]]
    assert "OCR OUTPUT TRUNCATED" in fallback
    assert len(fallback) < 1_200


def test_session_log_omits_inline_image_data() -> None:
    data_url = "data:image/png;base64,AAAA"
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "inspect /tmp/flag.png"},
                {
                    "type": "image_url",
                    "image_url": {"url": data_url, "detail": "auto"},
                },
            ],
        }
    ]

    sanitized = _sanitize_messages_for_log(messages)

    assert data_url not in str(sanitized)
    assert data_url in str(messages)
    assert sanitized[0]["content"][1] == {
        "type": "text",
        "text": "[PKS inline image omitted from session log]",
    }
