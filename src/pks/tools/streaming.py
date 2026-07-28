"""Output streaming utilities for tool execution.

Provides helpers to check streaming state and gather agent token
information for display in streaming panels.
"""

import contextvars
import os
from typing import Any

from pks.util import normalize_token_info


# Tool execution can run in child asyncio tasks where the model-level
# ``current_active_model`` ContextVar is absent or stale.  Carry the actual
# Agent object selected by Runner alongside the tool invocation instead of
# guessing ownership from the global model registry.
_TOOL_EXECUTION_AGENT_CONTEXT: contextvars.ContextVar[dict[str, Any] | None] = (
    contextvars.ContextVar("pks_tool_execution_agent", default=None)
)


def push_tool_execution_agent(agent: Any) -> contextvars.Token[dict[str, Any] | None]:
    """Bind the real tool-owning agent to the current async execution context."""
    model = getattr(agent, "model", None)
    agent_name = (
        getattr(agent, "name", None)
        or getattr(model, "agent_name", None)
        or "Agent"
    )
    agent_id = getattr(model, "agent_id", None)
    if not agent_id:
        try:
            from pks.sdk.agents.simple_agent_manager import AGENT_MANAGER

            agent_id = AGENT_MANAGER.get_agent_id()
        except Exception:
            agent_id = None
    return _TOOL_EXECUTION_AGENT_CONTEXT.set(
        {"agent_name": agent_name, "agent_id": agent_id, "model": model}
    )


def pop_tool_execution_agent(
    token: contextvars.Token[dict[str, Any] | None],
) -> None:
    """Restore the previous tool-owner context."""
    _TOOL_EXECUTION_AGENT_CONTEXT.reset(token)


def _tool_display_name(agent_name: str, agent_id: str | None) -> str:
    """Render parallel IDs, but keep the primary single-agent slot (P0) hidden."""
    if agent_id and agent_id != "P0" and f"[{agent_id}]" not in agent_name:
        return f"{agent_name} [{agent_id}]"
    return agent_name


def _get_idle_timeout() -> int:
    """Get the idle timeout from PKS_IDLE_TIMEOUT env var, default 100 seconds."""
    try:
        return int(os.getenv("PKS_IDLE_TIMEOUT", "100"))
    except ValueError:
        return 100


def is_tool_streaming_enabled() -> bool:
    """
    Check if tool output streaming is enabled.

    PKS_TOOL_STREAM controls tool output streaming (default: true)
    PKS_STREAM is ONLY for LLM inference streaming - does NOT affect tools.

    Tools stream by default. Only PKS_TOOL_STREAM=false disables it.
    """
    tool_stream_env = os.getenv("PKS_TOOL_STREAM")
    if tool_stream_env is not None:
        return tool_stream_env.lower() != "false"
    return True  # Default: streaming enabled for tools


def _get_agent_token_info():
    """Get token/display metadata for the agent that actually owns this tool call."""
    execution_context = _TOOL_EXECUTION_AGENT_CONTEXT.get()

    # Prefer the explicit Runner-provided tool owner.  The model ContextVar is
    # only a compatibility fallback because async generators/child tasks do not
    # guarantee that model-local context reaches the tool executor.
    try:
        from pks.sdk.agents.models.openai_chatcompletions import get_current_active_model

        model = (execution_context or {}).get("model") or get_current_active_model()

        if model:
            agent_name = str(
                (execution_context or {}).get("agent_name")
                or getattr(model, "agent_name", None)
                or "Agent"
            )
            agent_id = (execution_context or {}).get("agent_id")
            if agent_id is None:
                agent_id = getattr(model, "agent_id", None)
            display_name = _tool_display_name(agent_name, agent_id)

            token_info = {
                "agent_name": display_name,
                "agent_id": agent_id,
                "interaction_counter": getattr(model, "interaction_counter", 0),
                "total_input_tokens": getattr(model, "total_input_tokens", 0),
                "total_output_tokens": getattr(model, "total_output_tokens", 0),
                "total_reasoning_tokens": getattr(model, "total_reasoning_tokens", 0),
                "model": str(
                    getattr(
                        model,
                        "_current_request_model",
                        getattr(model, "model", os.environ.get("PKS_MODEL", "")),
                    )
                ),
            }

            token_info["interaction_input_tokens"] = getattr(
                model, "interaction_input_tokens", 0
            )
            token_info["interaction_output_tokens"] = getattr(
                model, "interaction_output_tokens", 0
            )
            token_info["interaction_reasoning_tokens"] = getattr(
                model, "interaction_reasoning_tokens", 0
            )

            # Add terminal_id from streaming context if available
            if hasattr(model, "_streaming_context") and model._streaming_context:
                streaming_ctx = model._streaming_context
                if isinstance(streaming_ctx, dict) and "terminal_id" in streaming_ctx:
                    token_info["terminal_id"] = streaming_ctx["terminal_id"]
                    # Try to extract terminal number from terminal_id
                    terminal_id = streaming_ctx["terminal_id"]
                    if terminal_id and terminal_id.startswith("terminal-") and terminal_id[9:].isdigit():
                        token_info["terminal_number"] = int(terminal_id[9:])

            # If no terminal_id from streaming context, try to get from current context
            if "terminal_id" not in token_info:
                try:
                    # Try async context first
                    from pks.tui.core.execution_context import get_terminal_id_context
                    terminal_id = get_terminal_id_context()
                    if terminal_id:
                        token_info["terminal_id"] = terminal_id
                        if terminal_id.startswith("terminal-") and terminal_id[9:].isdigit():
                            token_info["terminal_number"] = int(terminal_id[9:])
                except ImportError:
                    pass

                # Try thread-local context as fallback
                if "terminal_id" not in token_info:
                    try:
                        from pks.tui.core.terminal_tracking import get_current_terminal_id
                        terminal_id = get_current_terminal_id()
                        if terminal_id:
                            token_info["terminal_id"] = terminal_id
                            if terminal_id.startswith("terminal-") and terminal_id[9:].isdigit():
                                token_info["terminal_number"] = int(terminal_id[9:])
                    except ImportError:
                        pass

            return normalize_token_info(token_info)

        # Compatibility fallback for callers outside Runner-managed tool calls.
        # Prefer the manager's active Agent; never infer ownership from an
        # arbitrary entry in ACTIVE_MODEL_INSTANCES (that caused stale labels
        # such as "Continuous Ops Agent" on CTF tool calls).
        from pks.sdk.agents.simple_agent_manager import AGENT_MANAGER

        active_agent = AGENT_MANAGER.get_active_agent()
        model = getattr(active_agent, "model", None) if active_agent else None
        if model:
            agent_name = str(
                getattr(active_agent, "name", None)
                or getattr(model, "agent_name", None)
                or "Agent"
            )
            agent_id = getattr(model, "agent_id", None) or AGENT_MANAGER.get_agent_id()
            token_info = (
                model.get_token_info()
                if hasattr(model, "get_token_info")
                else {
                    "interaction_counter": getattr(model, "interaction_counter", 0),
                    "total_input_tokens": getattr(model, "total_input_tokens", 0),
                    "total_output_tokens": getattr(model, "total_output_tokens", 0),
                    "total_reasoning_tokens": getattr(model, "total_reasoning_tokens", 0),
                    "model": str(getattr(model, "model", os.environ.get("PKS_MODEL", ""))),
                }
            )
            token_info.update(
                {
                    "agent_name": _tool_display_name(agent_name, agent_id),
                    "agent_id": agent_id,
                }
            )
            return normalize_token_info(token_info)
    except Exception:
        pass

    # Return default values if we can't get agent info
    return normalize_token_info(
        {
            "agent_name": "Agent",
            "agent_id": None,
            "interaction_counter": 0,
            "interaction_input_tokens": 0,
            "interaction_output_tokens": 0,
            "interaction_reasoning_tokens": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_reasoning_tokens": 0,
            "model": os.environ.get("PKS_MODEL", ""),
        }
    )
