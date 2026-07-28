"""Token counting utilities using tiktoken.

Provides consistent token counting for messages and text,
plus reasoning compatibility checks for Claude models.
"""

from __future__ import annotations

import os

import tiktoken


def _check_reasoning_compatibility(messages):
    """
    Check if message history is compatible with Claude reasoning/thinking.

    According to Claude 4 docs, when reasoning is enabled, the final assistant
    message must start with a thinking block. If there are assistant messages
    with regular text content, reasoning should be disabled.

    Args:
        messages: List of message dictionaries

    Returns:
        bool: True if compatible with reasoning, False otherwise
    """
    if not messages:
        return True  # Empty messages are compatible

    # Find the last assistant message
    last_assistant_msg = None
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            last_assistant_msg = msg
            break

    if not last_assistant_msg:
        return True  # No assistant messages, compatible

    # Check if the last assistant message has regular text content
    content = last_assistant_msg.get("content")
    if content:
        # If it's a string with text content, not compatible
        if isinstance(content, str) and content.strip():
            return False
        # If it's a list, check for text content blocks
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text" and block.get("text", "").strip():
                        return False

    # Check if message has tool_calls (these are compatible)
    if last_assistant_msg.get("tool_calls"):
        return True

    # If no content or only thinking blocks, it's compatible
    return True


def _chars_per_token() -> float:
    """Chars-per-token divisor for the fast estimate. Lower = more conservative
    (over-counts -> compacts earlier -> safer against overflow on token-dense hex/code).

    Default 3.0: real PKS transcripts measure ~2.87 chars/token (hex/paths/code are
    token-dense), and with the 80% compaction threshold a divisor up to ~3.5 stays safe.
    3.0 hugs the real workload while keeping margin for even denser challenges."""
    try:
        v = float(os.getenv("PKS_CHARS_PER_TOKEN", "3.0"))
        return v if v >= 1.0 else 3.0
    except (TypeError, ValueError):
        return 3.0


def _count_with_char_estimate(text_or_messages):
    """Fast token estimate: len(text)/chars_per_token. No per-call encoding pass, works
    for any model/provider, and thousands× faster than tiktoken on a long history."""
    cpt = _chars_per_token()

    def est(s):
        return (int(len(s) / cpt) + 1) if s else 0

    if isinstance(text_or_messages, str):
        return est(text_or_messages), 0
    if isinstance(text_or_messages, list):
        total = len(text_or_messages) * 4  # ChatML per-message overhead (matches tiktoken path)
        reasoning = 0
        for msg in text_or_messages:
            if not isinstance(msg, dict):
                continue
            if msg.get("role"):
                total += est(msg["role"])
            content = msg.get("content")
            if not content:
                continue
            if isinstance(content, str):
                t = est(content)
                total += t
                if msg.get("role") == "assistant":
                    reasoning += t
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        t = est(part["text"])
                        total += t
                        if msg.get("role") == "assistant":
                            reasoning += t
        return total, reasoning
    return 0, 0


def _count_with_tiktoken(text_or_messages):
    """Exact tiktoken counting (slower — re-encodes the whole history each call)."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:
        try:
            encoding = tiktoken.get_encoding("gpt2")
        except Exception:
            return _count_with_char_estimate(text_or_messages)

    if isinstance(text_or_messages, str):
        return len(encoding.encode(text_or_messages)), 0
    elif isinstance(text_or_messages, list):
        total_tokens = len(text_or_messages) * 4
        reasoning_tokens = 0
        for msg in text_or_messages:
            if isinstance(msg, dict):
                if "role" in msg:
                    total_tokens += len(encoding.encode(msg["role"]))
                if "content" in msg and msg["content"]:
                    if isinstance(msg["content"], str):
                        content_tokens = len(encoding.encode(msg["content"]))
                        total_tokens += content_tokens
                        if msg.get("role") == "assistant":
                            reasoning_tokens += content_tokens
                    elif isinstance(msg["content"], list):
                        for content_part in msg["content"]:
                            if isinstance(content_part, dict) and "text" in content_part:
                                part_tokens = len(encoding.encode(content_part["text"]))
                                total_tokens += part_tokens
                                if msg.get("role") == "assistant":
                                    reasoning_tokens += part_tokens
        return total_tokens, reasoning_tokens
    else:
        return 0, 0


def count_tokens_with_tiktoken(text_or_messages):
    """
    Count tokens for messages/text. Returns (input_tokens, reasoning_tokens).

    Defaults to a FAST char-based estimate (``PKS_CHARS_PER_TOKEN``, default 3.5) — on a
    long history that is thousands× faster than re-encoding with tiktoken every turn, and
    works for any model/provider. Set ``PKS_TOKEN_COUNT=tiktoken`` to force exact counting.
    (Name kept for backward compatibility with existing call sites.)
    """
    if not text_or_messages:
        return 0, 0
    if os.getenv("PKS_TOKEN_COUNT", "char").strip().lower() in ("tiktoken", "exact"):
        return _count_with_tiktoken(text_or_messages)
    return _count_with_char_estimate(text_or_messages)
