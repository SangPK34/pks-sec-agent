"""Shared cross-agent findings store — the PKS "blackboard".

Every PKS agent runs in ONE process and hands off to others, but each agent keeps its OWN
message history and handoffs strip tool output (``remove_all_tools``), so agents do not
naturally see what other agents did. This module is the shared memory that is injected into
EVERY agent's system prompt as ``<shared_findings>`` (see ``system_master_template.md``).

Bounded by design so it never fills up or bloats the prompt:

* **findings** (from ``note_finding`` / ``set_flag``) are *pinned* — kept as long-lived context;
  confirmed FLAGs are never dropped. Capped at ``PKS_BB_FIND_CAP`` (default 150), oldest
  non-flag findings roll off first.
* **commands** (auto-logged shell/tool calls) are a *sliding window* — only the last
  ``PKS_BB_CMD_CAP`` (default 50) are kept verbatim; older ones roll off.
* **tried** is a compact ``tool -> count`` tally of every command ever run this session, so
  even after verbose commands roll off, agents still know "nmap/zsteg/steghide already tried".

Disable with ``PKS_BLACKBOARD=false``. Stored as a small JSON file under ``~/.pks``.
"""

from __future__ import annotations

import json
import os
import pathlib
import threading
import time

_LOCK = threading.RLock()


def _enabled() -> bool:
    return os.getenv("PKS_BLACKBOARD", "true").strip().lower() not in ("0", "false", "no")


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, "")))
    except (TypeError, ValueError):
        return default


def _find_cap() -> int:
    return _int_env("PKS_BB_FIND_CAP", 150)


def _cmd_cap() -> int:
    return _int_env("PKS_BB_CMD_CAP", 50)


def _bb_path() -> pathlib.Path:
    # PKS_BB_FILE lets each concurrent PKS instance use its OWN blackboard file so
    # parallel solves of different challenges never cross-contaminate or reset each other.
    override = (os.getenv("PKS_BB_FILE") or "").strip()
    if override:
        p = pathlib.Path(os.path.expanduser(override))
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return p
    base = pathlib.Path(os.path.expanduser("~")) / ".pks"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception:
        base = pathlib.Path("/tmp")
    return base / "blackboard.json"


def _blank() -> dict:
    return {"session": None, "findings": [], "commands": [], "tried": {}}


def _load() -> dict:
    try:
        d = json.loads(_bb_path().read_text(encoding="utf-8"))
        for k in ("findings", "commands"):
            d.setdefault(k, [])
        d.setdefault("tried", {})
        return d
    except Exception:
        return _blank()


def _save(data: dict) -> None:
    try:
        _bb_path().write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def reset(session_id: str | None = None) -> None:
    """Clear the board at the start of a new session."""
    with _LOCK:
        d = _blank()
        d["session"] = session_id
        _save(d)


def _clip(s: str, n: int) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def add(kind: str, content: str, agent: str = "") -> None:
    """Record a PINNED finding/conclusion (flag, cred, artifact, dead-end, …)."""
    if not _enabled():
        return
    content = _clip(content, 500)
    if not content:
        return
    kind = (kind or "finding")[:16]
    entry = {"t": time.strftime("%H:%M:%S"), "agent": (agent or "agent")[:40], "kind": kind, "c": content}
    with _LOCK:
        d = _load()
        f = d["findings"]
        if f and f[-1].get("c") == content and f[-1].get("kind") == kind:
            return  # de-dup
        f.append(entry)
        # roll off oldest NON-flag findings if over cap (flags are never dropped)
        cap = _find_cap()
        if len(f) > cap:
            flags = [e for e in f if e.get("kind", "").upper() == "FLAG"]
            others = [e for e in f if e.get("kind", "").upper() != "FLAG"]
            others = others[-(max(1, cap - len(flags))):]
            d["findings"] = flags + others
        _save(d)


def note_command(agent: str, command: str, exit_code=None, output: str = "") -> None:
    """Auto-log a shell/tool command (sliding window) + bump the tool tally."""
    if not _enabled():
        return
    command = _clip(command, 260)
    if not command:
        return
    tag = "ok" if str(exit_code) in ("0", "None", "") else f"exit{exit_code}"
    head = _clip(output, 160)
    tool = command.split()[0] if command.split() else command
    tool = tool[:24]
    entry = {"t": time.strftime("%H:%M:%S"), "agent": (agent or "agent")[:40], "tag": tag,
             "cmd": command, "head": head}
    with _LOCK:
        d = _load()
        c = d["commands"]
        if c and c[-1].get("cmd") == command:
            return  # de-dup consecutive identical commands
        c.append(entry)
        if len(c) > _cmd_cap():
            d["commands"] = c[-_cmd_cap():]
        tried = d["tried"]
        tried[tool] = int(tried.get(tool, 0)) + 1
        if len(tried) > 120:  # keep the tally itself bounded
            d["tried"] = dict(sorted(tried.items(), key=lambda kv: -kv[1])[:120])
        _save(d)


def read_state() -> dict:
    with _LOCK:
        return _load()


def render_block(max_findings: int = 40, max_commands: int = 40) -> str:
    """Render the board for injection into an agent system prompt (compact, always bounded)."""
    if not _enabled():
        return ""
    d = read_state()
    findings, commands, tried = d["findings"], d["commands"], d["tried"]
    if not findings and not commands:
        return ""
    out: list[str] = []

    flags = [e for e in findings if e.get("kind", "").upper() == "FLAG"]
    if flags:
        out.append("CONFIRMED FLAG(S): " + " ; ".join(e["c"] for e in flags[-5:]))

    notes = [e for e in findings if e.get("kind", "").upper() != "FLAG"]
    if notes:
        shown = notes[-max_findings:]
        if len(notes) > len(shown):
            out.append(f"Findings (pinned, {len(notes) - len(shown)} older omitted):")
        else:
            out.append("Findings (pinned):")
        out += [f"  • [{e['agent']}/{e['kind']}] {e['c']}" for e in shown]

    if tried:
        top = sorted(tried.items(), key=lambda kv: -kv[1])[:40]
        out.append("Commands/tools already used this session: "
                   + ", ".join(f"{k}×{v}" if v > 1 else k for k, v in top))

    if commands:
        shown = commands[-max_commands:]
        out.append(f"Recent commands (last {len(shown)}):")
        out += [f"  [{e['agent']}][{e['tag']}] {e['cmd']}"
                + (f" -> {e['head']}" if e.get("head") else "") for e in shown]

    return "\n".join(out)
