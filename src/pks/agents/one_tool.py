"""Backward-compatible import shim for the former one_tool module."""

from __future__ import annotations

from pks.agents.ctf_agent import ctf_agent as _ctf_agent
from pks.agents.ctf_agent import transfer_to_ctf_agent

__all__ = [
    "ctf_agent",
    "one_tool_agent",
    "transfer_to_ctf_agent",
    "transfer_to_one_tool_agent",
]


def transfer_to_one_tool_agent(**kwargs):  # pylint: disable=W0613
    """Legacy handoff alias for the CTF specialist."""
    return _ctf_agent


def __getattr__(name: str):
    if name in {"ctf_agent", "one_tool_agent"}:
        return _ctf_agent
    raise AttributeError(name)
