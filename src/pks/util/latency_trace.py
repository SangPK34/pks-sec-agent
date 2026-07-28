"""Opt-in monotonic latency trace for the model continuation path."""

from __future__ import annotations

import contextvars
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_TRACE_VALUES = {"1", "true", "yes", "on"}
_WRITE_LOCK = threading.Lock()
_CURRENT_TRACE: contextvars.ContextVar["LatencyTrace | None"] = contextvars.ContextVar(
    "pks_latency_trace",
    default=None,
)


def latency_trace_enabled() -> bool:
    return os.getenv("PKS_LATENCY_TRACE", "").strip().lower() in _TRACE_VALUES


def _trace_path() -> Path:
    configured = os.getenv("PKS_LATENCY_TRACE_FILE", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".pks" / "logs" / "latency.jsonl"


def _write(record: dict[str, Any]) -> None:
    if not latency_trace_enabled():
        return
    try:
        path = _trace_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _WRITE_LOCK, path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        pass


@dataclass(slots=True)
class LatencyTrace:
    agent_name: str
    phase: str
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: float = field(default_factory=time.monotonic)
    _seen: set[str] = field(default_factory=set)

    def mark(self, event: str, *, once: bool = False, **fields: Any) -> None:
        if once and event in self._seen:
            return
        self._seen.add(event)
        now = time.monotonic()
        _write(
            {
                "event": event,
                "trace_id": self.trace_id,
                "agent": self.agent_name,
                "phase": self.phase,
                "monotonic": now,
                "elapsed": now - self.started_at,
                **fields,
            }
        )


def begin_latency_trace(
    agent_name: str,
    phase: str,
) -> tuple[LatencyTrace, contextvars.Token[LatencyTrace | None]]:
    trace = LatencyTrace(agent_name=agent_name or "Agent", phase=phase)
    token = _CURRENT_TRACE.set(trace)
    trace.mark("continuation_request_start")
    return trace, token


def end_latency_trace(token: contextvars.Token[LatencyTrace | None]) -> None:
    _CURRENT_TRACE.reset(token)


def mark_latency(event: str, *, once: bool = False, **fields: Any) -> None:
    trace = _CURRENT_TRACE.get()
    if trace is not None:
        trace.mark(event, once=once, **fields)


def record_latency_event(event: str, **fields: Any) -> None:
    """Record an event outside a model request, such as tool completion."""
    now = time.monotonic()
    _write({"event": event, "monotonic": now, **fields})

