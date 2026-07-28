from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image

from pks.sdk.agents import ModelSettings, ModelTracing, generation_span
from pks.sdk.agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from pks.util.vision import PreparedVisionInput


def _write_png(path: Path) -> None:
    Image.new("RGB", (12, 8), "white").save(path, "PNG")


def _append_tool_image(model: OpenAIChatCompletionsModel, path: Path) -> None:
    call_id = "call_visual_test"
    model.add_to_message_history(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": "generic_linux_command",
                        "arguments": "{}",
                    },
                }
            ],
        }
    )
    model.add_to_message_history(
        {
            "role": "tool",
            "tool_call_id": call_id,
            "content": f"{path}: PNG image data, 12 x 8",
        }
    )


async def _fetch(model: OpenAIChatCompletionsModel) -> Any:
    with generation_span(disabled=True) as span:
        return await model._fetch_response(
            system_instructions=None,
            input=[],
            model_settings=ModelSettings(),
            tools=[],
            output_schema=None,
            handoffs=[],
            span=span,
            tracing=ModelTracing.DISABLED,
            stream=False,
        )


def _has_inline_image(messages: list[dict[str, Any]]) -> bool:
    return any(
        isinstance(message.get("content"), list)
        and any(
            isinstance(part, dict) and part.get("type") == "image_url"
            for part in message["content"]
        )
        for message in messages
    )


@pytest.mark.asyncio
async def test_new_tool_image_is_attached_once_without_prompt_keywords(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_path = tmp_path / "fixed.png"
    _write_png(image_path)
    model = OpenAIChatCompletionsModel(
        model="openai/CAI",
        openai_client=SimpleNamespace(),
        agent_name=f"vision-artifact-{id(image_path)}",
    )
    _append_tool_image(model, image_path)
    calls: list[list[dict[str, Any]]] = []

    async def fake_direct(kwargs, *_args, **_kwargs):
        calls.append(kwargs["messages"])
        return SimpleNamespace()

    monkeypatch.setattr(model, "_direct_httpx_completion", fake_direct)
    monkeypatch.setattr(
        PreparedVisionInput,
        "ocr_evidence",
        lambda _self: "OCR assist evidence",
    )

    await _fetch(model)
    await _fetch(model)

    assert _has_inline_image(calls[0])
    assert not _has_inline_image(calls[1])
    assert "base64," not in str(model.message_history)


@pytest.mark.asyncio
async def test_tool_image_retries_with_ocr_when_provider_rejects_vision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_path = tmp_path / "fixed.png"
    _write_png(image_path)
    model = OpenAIChatCompletionsModel(
        model="openai/CAI",
        openai_client=SimpleNamespace(),
        agent_name=f"vision-fallback-{id(image_path)}",
    )
    _append_tool_image(model, image_path)
    calls: list[list[dict[str, Any]]] = []

    async def fake_direct(kwargs, *_args, **_kwargs):
        calls.append(kwargs["messages"])
        if len(calls) == 1:
            raise RuntimeError("image_url is not supported")
        return SimpleNamespace()

    monkeypatch.setattr(model, "_direct_httpx_completion", fake_direct)
    monkeypatch.setattr(
        PreparedVisionInput,
        "ocr_evidence",
        lambda _self: "OCR fallback evidence",
    )

    await _fetch(model)

    assert _has_inline_image(calls[0])
    assert not _has_inline_image(calls[1])
    assert calls[1][-1]["role"] == "user"
    assert calls[1][-1]["content"].endswith("OCR fallback evidence")
    assert model._pks_native_vision_disabled is True
