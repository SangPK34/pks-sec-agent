"""Model-selected local image inspection."""

from __future__ import annotations

from pks.sdk.agents import function_tool
from pks.tools.common import _get_workspace_dir
from pks.util.vision import resolve_local_image_path


@function_tool
def view_image(paths: list[str]) -> str:
    """Load local image pixels into the model's next turn.

    Call this only when visual inspection is relevant to the current objective.
    Merely seeing an image filename or path is not a reason to call it.

    Args:
        paths: Local image paths to inspect, in the desired inspection order.
    """
    if not paths:
        return "No images selected."

    selected: list[str] = []
    errors: list[str] = []
    for raw in paths[:4]:
        try:
            path = resolve_local_image_path(raw, (_get_workspace_dir(),))
            from PIL import Image

            with Image.open(path) as image:
                image_format = (image.format or "image").upper()
                width, height = image.size
            selected.append(f"{path}: {image_format} image data, {width} x {height}")
        except (OSError, ValueError) as exc:
            errors.append(f"{raw}: {exc}")

    lines = ["[PKS view_image selection]"]
    lines.extend(selected)
    lines.extend(f"ERROR: {error}" for error in errors)
    if len(paths) > 4:
        lines.append(f"{len(paths) - 4} image(s) omitted; select them in another call.")
    return "\n".join(lines)
