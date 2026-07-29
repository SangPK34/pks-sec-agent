import json
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from PIL import Image
from rich.console import Console

from pks.output import VisionCompleteEvent
from pks.sdk.agents import ModelSettings, ModelTracing, generation_span
from pks.sdk.agents.models.chatcompletions import httpx_client
from pks.sdk.agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from pks.util.vision import PreparedVisionInput


def _write_png(path: Path) -> None:
    Image.new("RGB", (12, 8), "white").save(path, "PNG")


def _append_tool_image(
    model: OpenAIChatCompletionsModel,
    path: Path,
    working_directory: Path | None = None,
    tool_name: str = "view_image",
) -> None:
    call_id = "call_visual_test"
    arguments = (
        {"working_directory": str(working_directory)}
        if working_directory is not None
        else {}
    )
    model.add_to_message_history(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(arguments),
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


async def _fetch_stream(model: OpenAIChatCompletionsModel) -> Any:
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
            stream=True,
        )


def _mock_httpx_transport(
    monkeypatch: pytest.MonkeyPatch,
    handler: Any,
) -> None:
    async_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def create_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return async_client(*args, **kwargs)

    monkeypatch.setattr(httpx_client.httpx, "AsyncClient", create_client)


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
async def test_view_image_selection_is_attached_once(
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
    events: list[Any] = []

    async def fake_direct(kwargs, *_args, **_kwargs):
        calls.append(kwargs["messages"])
        return SimpleNamespace()

    monkeypatch.setattr(model, "_direct_httpx_completion", fake_direct)
    monkeypatch.setattr(
        "pks.sdk.agents.models.openai_chatcompletions.OUTPUT.emit",
        events.append,
    )
    monkeypatch.setattr(
        PreparedVisionInput,
        "ocr_evidence",
        lambda _self: pytest.fail("native Vision must not run OCR"),
    )

    await _fetch(model)
    await _fetch(model)

    assert _has_inline_image(calls[0])
    assert not _has_inline_image(calls[1])
    assert "base64," not in str(model.message_history)
    vision_events = [event for event in events if isinstance(event, VisionCompleteEvent)]
    assert len(vision_events) == 1
    assert vision_events[0].image_count == 1
    assert vision_events[0].image_paths == (str(image_path),)
    assert vision_events[0].mode == "vision"
    assert model._pks_vision_status is None


@pytest.mark.asyncio
async def test_generic_tool_image_output_does_not_trigger_vision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_path = tmp_path / "mentioned.png"
    _write_png(image_path)
    model = OpenAIChatCompletionsModel(
        model="openai/CAI",
        openai_client=SimpleNamespace(),
        agent_name="vision-not-selected",
    )
    _append_tool_image(
        model,
        image_path,
        tool_name="generic_linux_command",
    )
    calls: list[list[dict[str, Any]]] = []

    async def fake_direct(kwargs, *_args, **_kwargs):
        calls.append(kwargs["messages"])
        return SimpleNamespace()

    monkeypatch.setattr(model, "_direct_httpx_completion", fake_direct)

    await _fetch(model)

    assert not _has_inline_image(calls[0])


@pytest.mark.asyncio
async def test_extensionless_jpeg_selected_by_view_image_is_attached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_path = tmp_path / "file"
    Image.new("RGB", (20, 10), "white").save(image_path, "JPEG")
    model = OpenAIChatCompletionsModel(
        model="openai/CAI",
        openai_client=SimpleNamespace(),
        agent_name="vision-extensionless-artifact",
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
        lambda _self: pytest.fail("native Vision must not run OCR"),
    )
    monkeypatch.setattr(
        "pks.sdk.agents.models.openai_chatcompletions.OUTPUT.emit",
        lambda _event: None,
    )

    await _fetch(model)

    assert _has_inline_image(calls[0])
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
    events: list[Any] = []

    async def fake_direct(kwargs, *_args, **_kwargs):
        calls.append(kwargs["messages"])
        if len(calls) == 1:
            raise RuntimeError("image_url is not supported")
        return SimpleNamespace()

    monkeypatch.setattr(model, "_direct_httpx_completion", fake_direct)
    monkeypatch.setattr(
        "pks.sdk.agents.models.openai_chatcompletions.OUTPUT.emit",
        events.append,
    )
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
    assert model._pks_native_vision_disabled is False
    vision_events = [event for event in events if isinstance(event, VisionCompleteEvent)]
    assert len(vision_events) == 1
    assert vision_events[0].mode == "ocr_fallback"
    assert model._pks_vision_status is None


@pytest.mark.asyncio
async def test_streaming_vision_rejection_falls_back_before_stream_is_returned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_path = tmp_path / "stream.png"
    _write_png(image_path)
    model = OpenAIChatCompletionsModel(
        model="openai/CAI",
        openai_client=SimpleNamespace(),
        agent_name=f"vision-stream-fallback-{id(image_path)}",
    )
    _append_tool_image(model, image_path)
    requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        if _has_inline_image(body["messages"]):
            return httpx.Response(
                415,
                json={"error": {"message": "image_url is not supported"}},
            )
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text=(
                'data: {"id":"fallback","model":"test","choices":'
                '[{"delta":{"content":"OCR ok"},"finish_reason":null}]}\n\n'
                "data: [DONE]\n\n"
            ),
        )

    _mock_httpx_transport(monkeypatch, handler)
    monkeypatch.setattr(
        PreparedVisionInput,
        "ocr_evidence",
        lambda _self: "OCR fallback evidence",
    )

    _response, stream = await _fetch_stream(model)
    try:
        chunks = [chunk async for chunk in stream]

        assert len(requests) == 2
        assert _has_inline_image(requests[0]["messages"])
        assert not _has_inline_image(requests[1]["messages"])
        assert requests[1]["messages"][-1]["content"].endswith(
            "OCR fallback evidence"
        )
        assert chunks[0].choices[0].delta["content"] == "OCR ok"
        assert model._pks_seen_visual_artifacts
    finally:
        model._finish_vision_status(completed=False)


@pytest.mark.asyncio
async def test_streaming_vision_failure_does_not_mark_artifact_seen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_path = tmp_path / "failed-stream.png"
    _write_png(image_path)
    model = OpenAIChatCompletionsModel(
        model="openai/CAI",
        openai_client=SimpleNamespace(),
        agent_name=f"vision-stream-failed-{id(image_path)}",
    )
    _append_tool_image(model, image_path)
    requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        status = 415 if _has_inline_image(body["messages"]) else 422
        return httpx.Response(
            status,
            json={"error": {"message": "unsupported image request"}},
        )

    _mock_httpx_transport(monkeypatch, handler)
    monkeypatch.setattr(
        PreparedVisionInput,
        "ocr_evidence",
        lambda _self: "OCR fallback evidence",
    )

    with pytest.raises(httpx.HTTPStatusError):
        await _fetch_stream(model)

    assert len(requests) == 2
    assert not model._pks_seen_visual_artifacts
    assert model._pks_vision_status is None


@pytest.mark.asyncio
async def test_explicit_inline_image_emits_native_vision_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = OpenAIChatCompletionsModel(
        model="openai/CAI",
        openai_client=SimpleNamespace(),
        agent_name="vision-inline-status",
    )
    model.add_to_message_history(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "describe this"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "data:image/png;base64,AAAA",
                        "detail": "auto",
                    },
                },
            ],
        }
    )
    events: list[Any] = []

    async def fake_direct(*_args, **_kwargs):
        return SimpleNamespace()

    monkeypatch.setattr(model, "_direct_httpx_completion", fake_direct)
    monkeypatch.setattr(
        "pks.sdk.agents.models.openai_chatcompletions.OUTPUT.emit",
        events.append,
    )

    await _fetch(model)

    vision_events = [event for event in events if isinstance(event, VisionCompleteEvent)]
    assert len(vision_events) == 1
    assert vision_events[0].image_count == 1
    assert vision_events[0].mode == "vision"


@pytest.mark.asyncio
async def test_vision_status_is_cleaned_when_request_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_path = tmp_path / "failed.png"
    _write_png(image_path)
    model = OpenAIChatCompletionsModel(
        model="openai/CAI",
        openai_client=SimpleNamespace(),
        agent_name="vision-error-cleanup",
    )
    _append_tool_image(model, image_path)

    async def fake_direct(*_args, **_kwargs):
        raise RuntimeError("connection closed")

    monkeypatch.setattr(model, "_direct_httpx_completion", fake_direct)
    monkeypatch.setattr(
        PreparedVisionInput,
        "ocr_evidence",
        lambda _self: "OCR assist evidence",
    )

    with pytest.raises(RuntimeError, match="connection closed"):
        await _fetch(model)

    assert model._pks_vision_status is None
    from pks.util import wait_hints

    assert f"vision:{id(model)}" not in wait_hints._activity_overlays


def test_tui_vision_status_only_persists_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writes: list[Any] = []
    terminal = SimpleNamespace(write=writes.append)
    model = OpenAIChatCompletionsModel(
        model="openai/CAI",
        openai_client=SimpleNamespace(),
        agent_name="vision-tui-status",
    )
    monkeypatch.setenv("PKS_TUI_MODE", "true")
    monkeypatch.setattr(
        "pks.tui.core.terminal_console.get_terminal_output",
        lambda: terminal,
    )
    monkeypatch.setattr(
        "pks.sdk.agents.models.openai_chatcompletions.OUTPUT.emit",
        lambda _event: None,
    )

    model._start_vision_status(
        2,
        "vision_ocr",
        ("/tmp/first.png", "/tmp/second.png"),
    )
    model._finish_vision_status()

    assert len(writes) == 1
    output = StringIO()
    Console(file=output, force_terminal=False).print(writes[0])
    rendered = output.getvalue().splitlines()
    assert not any("Đang soi 2 ảnh" in item for item in rendered)
    assert len(rendered) == 6
    assert rendered[0] == "• Viewed Image"
    assert "/tmp/first.png" in rendered[1]
    assert rendered[2] == ""
    assert rendered[3] == "• Viewed Image"
    assert "/tmp/second.png" in rendered[4]
    assert rendered[5] == ""
