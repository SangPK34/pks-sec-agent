"""Worker-display silencing context for sub-agent runs.

Lives in :mod:`pks.util` (not :mod:`pks.sdk.agents`) so that user-facing display
routines like :mod:`pks.util.streaming` can ``import`` it at module load time
without triggering the heavy ``pks.sdk.agents`` package initialiser — that
package itself eagerly pulls :mod:`pks.util` and Rich
streaming helpers, so importing it from ``streaming`` would create a partially
initialised-module circular import.

Background
----------
The orchestration agent (``pks.agents.orchestration_agent``) calls specialist
agents as *tools* via :func:`pks.tools.misc.approach_contest.run_specialist`
(and ``run_dual_approach_contest`` for parallel A/B contests). Each tool
invocation spawns a fresh :class:`pks.sdk.agents.Runner.run` against a worker
agent, whose lifecycle naturally produces:

* Final markdown panels rendered by :func:`pks.util.streaming.cli_print_agent_messages`
  (the "● Red Team Agent (gpt-5.6-terra) ── <conclusion>" boxes).
* Streaming Rich panels created on the model side
  (:mod:`pks.sdk.agents.models.openai_chatcompletions`).

These outputs are *internal scratch* for the orchestrator — the user is only
ever supposed to see the orchestrator's final synthesis. Letting the worker
panels leak through gives the impression that two agents are answering the
same question, with the worker pre-empting the orchestrator's wording.

Mechanism
---------
A single :class:`contextvars.ContextVar` plus a
:func:`silence_worker_display` ``contextmanager``. Display routines that
should be skipped while a worker is running consult
:func:`worker_display_silenced` and bail out early. The flag is set by
``_run_worker`` in :mod:`pks.tools.misc.approach_contest` and is automatically
restored on exit (re-entrancy safe — nested workers stay silent).

What is **not** silenced
------------------------
The compact REPL live block (:mod:`pks.repl.ui.compact_renderer`) keeps showing
the worker's individual tool rows (``↳ ● Red Team Agent ─ nmap …``) because
those are progress feedback the user wants to see. Only the final-panel /
streaming-panel routes are gated on this flag.
"""

from __future__ import annotations

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager

_WORKER_DISPLAY_SILENT: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "pks_worker_display_silent",
    default=False,
)


@contextmanager
def silence_worker_display() -> Iterator[None]:
    """Silence per-message display while a sub-agent runs as a tool worker.

    The context is **inherited** by tasks spawned via :mod:`asyncio` because
    ``ContextVar`` values are copied into each new task's context. Nested
    contexts are safe: re-entering :func:`silence_worker_display` while the
    flag is already on is a no-op for the consumer (still ``True``), and the
    inner ``__exit__`` restores the prior ``True`` rather than dropping back
    to ``False``.
    """
    token = _WORKER_DISPLAY_SILENT.set(True)
    try:
        yield
    finally:
        _WORKER_DISPLAY_SILENT.reset(token)


def worker_display_silenced() -> bool:
    """Return ``True`` while a sub-agent run is suppressing user-facing display."""
    return _WORKER_DISPLAY_SILENT.get()


__all__ = ["silence_worker_display", "worker_display_silenced"]
