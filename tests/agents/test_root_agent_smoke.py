"""
Import-time smoke tests for the default Root Agent (heavier dependency graph).

Marked `slow` so fast slices can use `pytest -m "not slow"`.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


def test_root_agent_has_direct_tool_and_handoffs() -> None:
    from pks.agents.operational_handoffs import handoff_task_filter
    from pks.agents.root_agent import root_agent

    assert root_agent.name == "Root Agent"
    assert any(getattr(tool, "name", "") == "generic_linux_command" for tool in root_agent.tools)
    assert len(root_agent.handoffs) >= 1
    for ho in root_agent.handoffs:
        assert getattr(ho, "input_filter", None) is handoff_task_filter
        assert getattr(ho, "tool_name", None)
        desc = getattr(ho, "tool_description", "") or ""
        assert len(desc) > 20
