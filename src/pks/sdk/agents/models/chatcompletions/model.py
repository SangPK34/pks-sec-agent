"""Shared model-instance state used by the Chat Completions implementation."""

from __future__ import annotations

import contextvars
import os
import weakref

from pks.sdk.agents.simple_agent_manager import AGENT_MANAGER
from pks.sdk.agents.models.chatcompletions.stream_handler import StreamingState

ACTIVE_MODEL_INSTANCES = {}
PERSISTENT_MESSAGE_HISTORIES = {}
_PREVIOUS_TURN_MSG_HASHES = []
_compaction_in_progress = False
_current_model_context = contextvars.ContextVar("current_model", default=None)
_StreamingState = StreamingState


def set_current_active_model(model):
    _current_model_context.set(weakref.ref(model) if model else None)


def get_current_active_model():
    model_ref = _current_model_context.get()
    return model_ref() if model_ref else None


def _base_agent_name(agent_name: str) -> str:
    if "[" in agent_name and agent_name.endswith("]"):
        return agent_name.rsplit("[", 1)[0].strip()
    return agent_name


def get_agent_message_history(agent_name: str) -> list:
    return AGENT_MANAGER.get_message_history(_base_agent_name(agent_name))


def get_all_agent_histories() -> dict:
    return AGENT_MANAGER.get_all_histories()


def clear_agent_history(agent_name: str):
    base_name = _base_agent_name(agent_name)
    AGENT_MANAGER.clear_history(base_name)
    active_agent = AGENT_MANAGER.get_active_agent()
    if (
        active_agent
        and hasattr(active_agent, "message_history")
        and getattr(active_agent, "agent_name", None) == base_name
    ):
        active_agent.message_history.clear()
        os.environ["PKS_CONTEXT_USAGE"] = "0.0"


def clear_all_histories():
    AGENT_MANAGER.clear_all_histories()
    active_agent = AGENT_MANAGER.get_active_agent()
    if active_agent and hasattr(active_agent, "message_history"):
        active_agent.message_history.clear()
    PERSISTENT_MESSAGE_HISTORIES.clear()
    os.environ["PKS_CONTEXT_USAGE"] = "0.0"
