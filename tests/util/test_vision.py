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
    input_has_images,
    is_vision_rejection,
    prepare_vision_input,
    remove_pending_vision_history,
)
from pks.sdk.agents.run_to_jsonl import _sanitize_messages_for_log


def _write_png(path: Path) -> None:
    Image.new("RGB", (8, 6), "white").save(path, "PNG")


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
