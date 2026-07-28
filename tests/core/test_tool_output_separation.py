from __future__ import annotations

import asyncio

from openai.types.responses import ResponseFunctionToolCall
from rich.console import Console

from pks.sdk.agents import Agent, RunConfig, RunContextWrapper, RunHooks, function_tool
from pks.sdk.agents._run_impl import (
    RunImpl,
    ToolRunFunction,
    _emit_compact_task_complete,
    truncate_output,
)
from pks.util.terminal import (
    _create_tool_panel_content,
    _prepare_tool_output_for_display,
)


def test_llm_output_is_exact_below_limit(monkeypatch):
    monkeypatch.setenv("PKS_TOOL_OUTPUT_MAX", "20000")
    raw_output = "exact tool output\n" * 500

    assert truncate_output(raw_output) == raw_output


def test_llm_output_never_exceeds_configured_limit(monkeypatch):
    monkeypatch.setenv("PKS_TOOL_OUTPUT_MAX", "800")

    assert len(truncate_output("x" * 10000)) <= 800


def test_ui_preview_has_independent_character_and_line_limits():
    raw_output = "\n".join(f"line-{index:03d}" for index in range(200))

    ui_display_output = _prepare_tool_output_for_display(
        "generic_linux_command", raw_output * 10
    )
    assert len(ui_display_output) <= 10000
    assert "... TRUNCATED ..." in ui_display_output

    _, renderable = _create_tool_panel_content(
        "generic_linux_command",
        {"command": "cat", "args": "large.txt"},
        raw_output,
        execution_info={"status": "completed"},
    )
    console = Console(record=True, width=120)
    console.print(renderable)
    rendered = console.export_text()

    assert "... (160 lines omitted) ..." in rendered
    assert "line-000" in rendered
    assert "line-199" in rendered
    assert "line-100" not in rendered


def test_simple_ui_preview_also_enforces_line_limit():
    raw_output = "\n".join(f"line-{index:03d}" for index in range(200))

    ui_display_output = _prepare_tool_output_for_display(
        "generic_linux_command",
        raw_output,
    )

    assert len(ui_display_output.splitlines()) == 41
    assert "... (160 lines omitted) ..." in ui_display_output
    assert "line-000" in ui_display_output
    assert "line-199" in ui_display_output
    assert "line-100" not in ui_display_output


def test_compact_task_registry_receives_ui_preview(monkeypatch):
    raw_output = "\n".join(f"line-{index:03d}" for index in range(200))
    emitted = []

    monkeypatch.setattr("pks.output.OUTPUT.emit", emitted.append)
    _emit_compact_task_complete("task-1", 0.0, raw_output)

    assert len(emitted) == 1
    ui_display_output = emitted[0].output
    assert len(ui_display_output) <= 10000
    assert len(ui_display_output.splitlines()) == 41
    assert "line-100" not in ui_display_output


def test_tool_result_keeps_raw_output_but_caps_llm_memory(monkeypatch):
    monkeypatch.setenv("PKS_TOOL_OUTPUT_MAX", "20000")
    monkeypatch.setenv("PKS_BLACKBOARD", "false")
    raw_output = "HEAD\n" + ("middle-data\n" * 5000) + "TAIL"

    def large_output_tool() -> str:
        return raw_output

    tool = function_tool(large_output_tool)
    agent = Agent(name="test", tools=[tool])
    tool_call = ResponseFunctionToolCall(
        id="item-1",
        call_id="call-1",
        type="function_call",
        name=tool.name,
        arguments="{}",
    )

    results = asyncio.run(
        RunImpl.execute_function_tool_calls(
            agent=agent,
            tool_runs=[ToolRunFunction(tool_call=tool_call, function_tool=tool)],
            hooks=RunHooks(),
            context_wrapper=RunContextWrapper(context=None),
            config=RunConfig(),
        )
    )

    assert len(results) == 1
    result = results[0]
    assert result.output == raw_output
    assert result.run_item.output == raw_output

    llm_memory_output = result.run_item.raw_item["output"]
    assert llm_memory_output != raw_output
    assert len(llm_memory_output) <= 20000
    assert "[truncated:" in llm_memory_output
    assert llm_memory_output.startswith("HEAD")
    assert llm_memory_output.endswith("TAIL")
