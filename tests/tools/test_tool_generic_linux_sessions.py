import os
import re
import json
import asyncio
from types import SimpleNamespace

import pytest

os.environ["OPENAI_API_KEY"] = "test_key_for_ci_environment"

from pks.sdk.agents import RunContextWrapper
from pks.tools.reconnaissance.generic_linux_command import generic_linux_command
from pks.tools import executor


def _extract_alias(msg: str) -> str | None:
    m = re.search(r"Started async session\s+(S\d+)", msg)
    return m.group(1) if m else None


@pytest.mark.asyncio
async def test_interactive_session_create_and_io():
    # Create a simple interactive session that emits one line then echoes stdin
    cmd = "sh -c 'printf ready\\n; cat -'"
    args = {"command": cmd, "interactive": True}
    out = await generic_linux_command.on_invoke_tool(RunContextWrapper(None), json.dumps(args))
    assert "Started async session" in out

    alias = _extract_alias(out)
    assert alias is not None

    # Read initial output (should contain 'ready')
    args = {"command": f"output {alias}"}
    out = await generic_linux_command.on_invoke_tool(RunContextWrapper(None), json.dumps(args))
    assert "ready" in out or "Started" in out

    # Send a line and expect to see it echoed back by cat -
    args = {"command": "hello-world", "session_id": alias}
    out = await generic_linux_command.on_invoke_tool(RunContextWrapper(None), json.dumps(args))
    assert "hello-world" in out

    # Kill the session
    args = {"command": f"kill {alias}"}
    out = await generic_linux_command.on_invoke_tool(RunContextWrapper(None), json.dumps(args))
    assert "terminated" in out.lower() or "already terminated" in out.lower()


@pytest.mark.asyncio
async def test_session_parsing_variants():
    # New interactive session
    cmd = "sh -c 'printf ready\\n; cat -'"
    args = {"command": cmd, "interactive": True}
    out = await generic_linux_command.on_invoke_tool(RunContextWrapper(None), json.dumps(args))
    alias = _extract_alias(out)
    assert alias is not None

    # Old variant: command="session", session_id="output S#"
    args = {"command": "session", "session_id": f"output {alias}"}
    out = await generic_linux_command.on_invoke_tool(RunContextWrapper(None), json.dumps(args))
    assert isinstance(out, str)
    assert "Session" not in out or "not found" not in out

    # status should return a string even if no new output
    args = {"command": f"status {alias}"}
    out = await generic_linux_command.on_invoke_tool(RunContextWrapper(None), json.dumps(args))
    assert isinstance(out, str)

    # Cleanup
    await generic_linux_command.on_invoke_tool(
        RunContextWrapper(None), json.dumps({"command": f"kill {alias}"})
    )


def test_session_input_is_sent_once_and_not_rendered_by_executor(monkeypatch):
    class FakeSession:
        friendly_id = "S-test"

        def __init__(self):
            self.inputs = []
            self.read_count = 0

        def send_input(self, value):
            self.inputs.append(value)

        def get_new_output(self, mark_position=True):
            self.read_count += 1
            return "" if self.read_count == 1 else "ack"

    session = FakeSession()
    rendered = []
    monkeypatch.setitem(executor.ACTIVE_SESSIONS, "session-test", session)
    monkeypatch.setattr(
        executor,
        "_get_config",
        lambda: SimpleNamespace(session_input_wait=0.2),
    )
    monkeypatch.setattr(executor.time, "sleep", lambda _seconds: None)

    import pks.util

    monkeypatch.setattr(
        pks.util,
        "cli_print_tool_output",
        lambda *args, **kwargs: rendered.append((args, kwargs)),
    )

    output = executor.run_command(
        "stateful-input",
        session_id="session-test",
        timeout=1,
        stream=False,
    )

    assert output == "ack"
    assert session.inputs == ["stateful-input"]
    assert rendered == []
