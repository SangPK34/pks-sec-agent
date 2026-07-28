"""Model context-window and compact token display helpers."""

from __future__ import annotations

import os
from typing import Any

from rich.text import Text

from pks.model_catalog import context_window_for_model


def get_model_name(model: Any) -> str:
    if isinstance(model, str):
        return model
    return os.environ.get("PKS_MODEL", "gpt-5.6-terra")


def get_model_input_tokens(model: Any) -> int:
    """Return the context-window estimate used by auto-compaction."""
    override = (os.getenv("PKS_MODEL_MAX_INPUT_TOKENS") or "").strip()
    if override:
        try:
            value = int(float(override))
            if value > 0:
                return value
        except ValueError:
            pass

    model_name = get_model_name(model).lower()
    catalog_limit = context_window_for_model(model_name)
    if catalog_limit:
        return catalog_limit
    limits = (
        ("gpt-5.6", 1_050_000),
        ("gpt-5.5", 1_000_000),
        ("gpt-5.4-mini", 400_000),
        ("gpt-5.4", 1_050_000),
        ("gpt-5.2", 400_000),
        ("gpt-5.1", 272_000),
        ("gpt-5-pro", 400_000),
        ("gpt-5", 272_000),
        ("gpt-4.1", 1_047_576),
        ("o4-mini", 200_000),
        ("o3", 200_000),
        ("o1", 200_000),
        ("deepseek-v4", 1_000_000),
        ("claude", 200_000),
    )
    for pattern, limit in limits:
        if pattern in model_name:
            return limit
    return 128_000


def _create_token_display(
    interaction_input_tokens: int,
    interaction_output_tokens: int,
    interaction_reasoning_tokens: int,
    total_input_tokens: int,
    total_output_tokens: int,
    total_reasoning_tokens: int,
    model: Any,
    cache_read_tokens: int | None = None,
    cache_creation_tokens: int | None = None,
    **_ignored: Any,
) -> Text:
    """Create token/context text without pricing or billing calculations."""
    del total_input_tokens, total_output_tokens, total_reasoning_tokens
    text = Text(justify="left")
    text.append("\n  Interaction: ", style="bold cyan")
    text.append(f"In: {interaction_input_tokens}", style="green")
    text.append(f" Out: {interaction_output_tokens}", style="yellow")
    text.append(f" R: {interaction_reasoning_tokens}", style="magenta")

    if cache_read_tokens:
        text.append(f" CR: {int(cache_read_tokens)}", style="green")
    if cache_creation_tokens:
        text.append(f" CW: {int(cache_creation_tokens)}", style="yellow")

    interaction_total = (
        interaction_input_tokens
        + interaction_output_tokens
        + interaction_reasoning_tokens
    )
    text.append(f" | Total: {interaction_total}", style="bold white")

    maximum = get_model_input_tokens(model)
    context_pct = (interaction_input_tokens / maximum * 100.0) if maximum else 0.0
    style = "bold red" if context_pct > 80 else "bold yellow" if context_pct > 50 else "green"
    text.append(f" | Context: {context_pct:.1f}%", style=style)
    return text


def _create_token_info_display(token_info: dict[str, Any] | None = None):
    if not token_info:
        return None
    interaction_input = int(token_info.get("interaction_input_tokens", 0) or 0)
    interaction_output = int(token_info.get("interaction_output_tokens", 0) or 0)
    interaction_reasoning = int(token_info.get("interaction_reasoning_tokens", 0) or 0)
    if not (interaction_input or interaction_output or interaction_reasoning):
        return None
    return _create_token_display(
        interaction_input_tokens=interaction_input,
        interaction_output_tokens=interaction_output,
        interaction_reasoning_tokens=interaction_reasoning,
        total_input_tokens=int(token_info.get("total_input_tokens", 0) or 0),
        total_output_tokens=int(token_info.get("total_output_tokens", 0) or 0),
        total_reasoning_tokens=int(token_info.get("total_reasoning_tokens", 0) or 0),
        model=token_info.get("model", os.getenv("PKS_MODEL", "")),
        cache_read_tokens=token_info.get("cache_read_tokens"),
        cache_creation_tokens=token_info.get("cache_creation_tokens"),
    )


def normalize_token_info(
    token_info: dict[str, Any] | None,
    *,
    default_model: str | None = None,
) -> dict[str, Any]:
    """Normalize token fields and derive context usage without pricing work."""
    normalized = dict(token_info or {})
    model = str(normalized.get("model") or default_model or os.getenv("PKS_MODEL", ""))
    normalized["model"] = model
    input_tokens = int(
        normalized.get("interaction_input_tokens", normalized.get("input_tokens", 0))
        or 0
    )
    normalized.setdefault("interaction_input_tokens", input_tokens)
    normalized.setdefault(
        "interaction_output_tokens",
        int(normalized.get("output_tokens", 0) or 0),
    )
    normalized.setdefault(
        "interaction_reasoning_tokens",
        int(normalized.get("reasoning_tokens", 0) or 0),
    )
    normalized.setdefault("total_input_tokens", input_tokens)
    normalized.setdefault(
        "total_output_tokens",
        normalized["interaction_output_tokens"],
    )
    normalized.setdefault(
        "total_reasoning_tokens",
        normalized["interaction_reasoning_tokens"],
    )
    normalized.setdefault("cache_read_tokens", 0)
    normalized.setdefault("cache_creation_tokens", 0)
    maximum = get_model_input_tokens(model)
    normalized["context_usage_pct"] = (
        input_tokens / maximum * 100.0 if maximum else 0.0
    )
    return normalized


def _get_timing_info(execution_info: dict[str, Any] | None = None):
    if not execution_info:
        return None
    tool_time = execution_info.get("tool_time")
    if not tool_time:
        return None
    from pks.util.terminal import format_time

    return format_time(tool_time)
