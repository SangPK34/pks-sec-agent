import asyncio
from io import StringIO
from types import SimpleNamespace

import pytest
from rich.console import Console
from rich.text import Text

import pks.util.streaming as streaming
import pks.util.wait_hints as wait_hints
from pks.output import TaskRecord
from pks.repl.ui.compact_renderer import CompactCLIHandler, _row_for_record
from pks.util.hint_renderables import build_model_wait_hint_renderable


def test_compact_owner_suppresses_legacy_footer_refresh(monkeypatch):
    calls = []

    def fake_refresh():
        calls.append("refresh")

    monkeypatch.setattr(
        "pks.util.streaming.refresh_tool_wait_displays",
        fake_refresh,
    )

    wait_hints.set_compact_live_owner(True)
    try:
        wait_hints._request_footer_ui_refresh()
    finally:
        wait_hints.set_compact_live_owner(False)

    assert calls == []


def test_clear_wait_hints_removes_published_body():
    wait_hints._set_model_wait_body("model wait")
    wait_hints._set_tool_wait_body("tool wait")

    assert wait_hints.get_current_wait_hint_body()

    wait_hints.clear_wait_hints()

    assert wait_hints.get_current_wait_hint_body() is None


@pytest.mark.asyncio
async def test_tool_wait_loop_under_compact_owner_only_publishes_body(monkeypatch):
    monkeypatch.setattr(wait_hints, "tool_wait_hints_enabled", lambda: True)

    wait_hints.set_compact_live_owner(True)
    loop = wait_hints._WaitHintLoop(
        mode="tool",
        tool_label="generic_linux_command",
        exec_summary="sleep 10",
    )
    try:
        await loop.start()

        assert wait_hints.get_current_wait_hint_body()
        assert wait_hints.get_tool_wait_footer_renderable() is None
    finally:
        await loop.stop()
        wait_hints.set_compact_live_owner(False)


def test_compact_final_dismiss_releases_ownership_on_flush(monkeypatch):
    owner_changes = []

    def fake_set_owner(active):
        owner_changes.append(active)

    monkeypatch.setattr("pks.util.wait_hints.set_compact_live_owner", fake_set_owner)

    handler = CompactCLIHandler(
        Console(file=StringIO(), force_terminal=True, width=80)
    )
    handler._owns_wait_hints = True

    handler.dismiss_for_final_output()
    assert owner_changes == []

    handler.flush()
    assert owner_changes == [False]


def test_finish_agent_streaming_clears_wait_ui_before_final(monkeypatch):
    calls = []

    def fake_prepare():
        calls.append("prepare")

    monkeypatch.setattr(streaming, "_prepare_terminal_for_final_agent_output", fake_prepare)

    context = {
        "content": Text("final answer"),
        "is_started": False,
        "context_key": "test",
        "header": Text("Agent"),
        "live": None,
    }
    streaming.create_agent_streaming_context._active_streaming = {"test": context}

    assert streaming.finish_agent_streaming(context, {"has_tool_calls": False}) is True
    assert calls == ["prepare"]


def test_cli_print_agent_messages_clears_wait_ui_before_final(monkeypatch):
    calls = []

    def fake_prepare():
        calls.append("prepare")

    monkeypatch.setattr(streaming, "_prepare_terminal_for_final_agent_output", fake_prepare)

    streaming.cli_print_agent_messages(
        agent_name="Agent",
        message=SimpleNamespace(content="final answer", tool_calls=None),
        counter=1,
        model="test-model",
        debug=False,
        suppress_empty=True,
    )

    assert calls == ["prepare"]


def test_compact_row_hides_primary_agent_id_and_agent_label():
    row = _row_for_record(
        TaskRecord(
            task_id="task-1",
            turn_id="turn-1",
            agent_name="Red Team Agent",
            agent_id="P0",
            tool_name="generic_linux_command",
            label="nmap -sV 127.0.0.1",
            started_at=0.0,
            call_id="call-1",
        ),
        now=1.0,
        tick=0,
    )

    assert "Red Team Agent ─ nmap" in row.plain
    assert "[P0]" not in row.plain
    assert " AGENT " not in row.plain


def test_compact_row_keeps_parallel_agent_id():
    row = _row_for_record(
        TaskRecord(
            task_id="task-1",
            turn_id="turn-1",
            agent_name="Red Team Agent",
            agent_id="P1",
            tool_name="generic_linux_command",
            label="nmap -sV 127.0.0.1",
            started_at=0.0,
            call_id="call-1",
        ),
        now=1.0,
        tick=0,
    )

    assert "Red Team Agent [P1] ─ nmap" in row.plain
    assert " AGENT " not in row.plain


def test_set_model_wait_retry_overlay_overrides_model_body():
    """``set_model_wait_retry_overlay`` shadows the default body and ``None`` clears it."""
    try:
        wait_hints.set_model_wait_retry_overlay("Rate budget reached, pacing for 5s…")
        body = wait_hints._model_body(0.0, {})
        assert body.startswith("Rate budget reached, pacing for 5s…")
        assert "Ctrl+C to interrupt" in body
    finally:
        wait_hints.set_model_wait_retry_overlay(None)
    state = {}
    first = wait_hints._model_body(0.0, state)
    second = wait_hints._model_body(10.0, state)
    assert first.split("  Ctrl+C", 1)[0] in wait_hints.MODEL_ACTIVITY_MESSAGES
    assert first.split("  Ctrl+C", 1)[0] == second.split("  Ctrl+C", 1)[0]


def test_model_wait_renderable_matches_command_code_chrome():
    rendered = build_model_wait_hint_renderable(
        "Architecting…  Ctrl+C to interrupt  •  1s"
    )

    assert rendered.plain.startswith("✶ ")
    assert "Architecting…" in rendered.plain
    assert "Ctrl+C to interrupt" in rendered.plain
    assert "↓ 0" in rendered.plain


def test_model_wait_renderable_animates_icon_and_badge():
    first = build_model_wait_hint_renderable(
        "Architecting…  Ctrl+C to interrupt  •  1s",
        frame_tick=0,
    )
    second = build_model_wait_hint_renderable(
        "Architecting…  Ctrl+C to interrupt  •  1s",
        frame_tick=1,
    )

    assert first.plain != second.plain
    assert first.spans != second.spans


def test_compact_handler_prints_thought_and_worked_notes(monkeypatch):
    output = StringIO()
    handler = CompactCLIHandler(
        Console(file=output, force_terminal=False, width=100)
    )
    monkeypatch.setattr(
        wait_hints,
        "consume_last_model_wait_duration",
        lambda: 1.2,
    )
    monkeypatch.setattr("pks.repl.ui.compact_renderer.time.monotonic", lambda: 13.0)
    monkeypatch.setattr("pks.repl.ui.compact_renderer.TASK_REGISTRY.for_turn", lambda: [])
    handler._turn_started_monotonic = 10.0

    handler._print_thought_note()
    handler._print_worked_note()

    text = output.getvalue()
    assert "✻ Thought for 1 second [Ctrl+O to expand]" in text
    assert "✻ Worked for 3.0s" in text


def test_model_wait_body_after_tool_output_uses_tool_phase():
    body = wait_hints._model_body(
        0.0,
        {"phase": "tool_result", "agent_name": "CTF agent"},
    )

    assert body.startswith("CTF agent đang phân tích kết quả tool…")
    assert body.endswith("0.0s")
    assert "Ctrl+C to interrupt" in body


@pytest.mark.asyncio
async def test_model_wait_spinner_runs_without_provider_events_and_cleans_up(monkeypatch):
    monkeypatch.setattr(wait_hints, "wait_hints_enabled", lambda: True)
    monkeypatch.setattr(wait_hints, "_compact_cli_owns_wait_hints", lambda: True)
    wait_hints.clear_wait_hints()

    hint = wait_hints.ModelStreamWaitHints(
        model_phase="tool_result",
        agent_name="CTF agent",
    )
    try:
        await hint.start()
        await asyncio.sleep(0.3)

        body = wait_hints.get_current_wait_hint_body()
        assert body is not None
        assert "CTF agent đang phân tích kết quả tool…" in body
        assert "0.3s" in body
    finally:
        await hint.stop()
        wait_hints.clear_wait_hints()

    assert wait_hints._current_model_body is None
    assert not any(
        task.get_name() == "pks_wait_hints" and not task.done()
        for task in asyncio.all_tasks()
    )


def test_compact_mode_renders_first_text_delta_immediately(monkeypatch):
    updates = []
    prepare_calls = []

    class FakeLive:
        def __init__(self, *args, **kwargs):
            self.transient = False

        def start(self, refresh=True):
            updates.append(("start", refresh))

        def update(self, content, refresh=False):
            updates.append(("update", refresh))

    monkeypatch.setattr(streaming, "_compact_suppresses_verbose", lambda: True)
    monkeypatch.setattr(
        streaming,
        "_prepare_terminal_for_final_agent_output",
        lambda: prepare_calls.append("prepare"),
    )
    monkeypatch.setattr(streaming, "_get_pks_agent_live_class", lambda: FakeLive)

    context = {
        "content": Text(""),
        "header": Text("● CTF agent"),
        "footer": Text(""),
        "timestamp": "00:00:00",
        "model": "test",
        "agent_name": "CTF agent",
        "is_started": False,
        "live": None,
        "context_key": "delta-test",
    }

    assert streaming.update_agent_streaming_content(context, "first", None) is True
    assert context["content"].plain == "first"
    assert context["is_started"] is True
    assert prepare_calls == ["prepare"]
    assert ("update", True) in updates

    assert streaming.update_agent_streaming_content(context, " second", None) is True
    assert context["content"].plain == "first second"
    assert updates[-1] == ("update", False)
