"""Compatibility shim for the former routing-agent module."""

from __future__ import annotations

from pks.agents.root_agent import root_agent, transfer_to_root_agent

__all__ = ["root_agent", "transfer_to_root_agent", "transfer_to_selection_agent"]


def transfer_to_selection_agent(**kwargs):  # pylint: disable=W0613
    """Backward-compatible handoff to the root agent."""
    return root_agent


def __getattr__(name: str):
    if name == "selection_agent":
        return root_agent
    raise AttributeError(name)
