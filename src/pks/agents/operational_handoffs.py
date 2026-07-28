"""Operational specialist handoffs shared by routing agents (root, orchestration)."""

from __future__ import annotations

import importlib
import json

from pydantic import BaseModel, Field

from pks.sdk.agents.extensions.handoff_filters import remove_all_tools
from pks.sdk.agents.handoffs import HandoffInputData, handoff
from pks.sdk.agents.items import HandoffCallItem


class _HandoffTask(BaseModel):
    """Structured brief the router must write when delegating to a specialist.

    Making the task explicit (a) forces the Root Agent to state exactly what it
    is delegating, and (b) lets the UI show it — so it is transparent what work, and
    what phrasing, each specialist received (no silent 'adding/dropping intent').
    """

    task: str = Field(
        ...,
        description=(
            "One or two concise technical ENGLISH sentences for the destination agent. "
            "Preserve exact paths, commands, artifacts, constraints, and the user's intent. "
            "Do NOT add scope, drop requirements, or invent targets."
        ),
    )


def handoff_task_filter(data: HandoffInputData) -> HandoffInputData:
    """Strip tool chatter while preserving the structured task as real input."""
    task = ""
    for item in reversed(data.new_items):
        if not isinstance(item, HandoffCallItem):
            continue
        try:
            args = json.loads(getattr(item.raw_item, "arguments", "") or "{}")
            task = str(args.get("task", "")).strip()
        except (TypeError, ValueError, json.JSONDecodeError):
            task = ""
        break

    filtered = remove_all_tools(data)
    if not task:
        return filtered

    task_block = (
        "<agent_handoff_task>\n"
        "Internal delegation brief (authoritative for this turn):\n"
        f"{task}\n"
        "</agent_handoff_task>"
    )
    if isinstance(filtered.input_history, str):
        history = f"{filtered.input_history.rstrip()}\n\n{task_block}"
    else:
        history = filtered.input_history + (
            {"role": "user", "content": task_block},
        )
    return HandoffInputData(
        input_history=history,
        pre_handoff_items=filtered.pre_handoff_items,
        new_items=filtered.new_items,
    )


def _announce_delegation(target_name: str, task: str) -> None:
    """Print a panel that makes the root -> specialist delegation (and its task) visible.

    Fires from the handoff's ``on_handoff`` callback, so it shows regardless of how tool
    calls are rendered in the current UI.
    """
    task = (task or "").strip()
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        body = Text(task or "(no task provided)", style="white")
        console = Console()
        console.print(
            Panel(
                body,
                title=f"[bold yellow]Root Agent  →  {target_name}[/bold yellow]",
                title_align="left",
                border_style="yellow",
                padding=(0, 1),
            )
        )
        console.print()  # trailing blank line so the next block doesn't overlap this panel
    except Exception:
        pass


def _make_on_handoff_task(target_name: str):
    """Bind the delegation target's name into the ``on_handoff`` callback."""

    def _cb(ctx, task_input):  # noqa: ANN001, ARG001
        _announce_delegation(target_name, getattr(task_input, "task", "") or "")

    return _cb


def operational_agent_factory_keys() -> list[str]:
    """Factory keys for specialists; contest workers use the same names."""
    return [attr for _, attr, _ in operational_agent_specs()]


def operational_agent_specs() -> list[tuple[str, str, str]]:
    """Module path, agent variable name, routing description."""
    return [
        (
            "pks.agents.red_teamer",
            "redteam_agent",
            "Use for broad offensive security: pentests, exploitation, privilege escalation, "
            "shell/CLI recon, and general attack-chain work (not single-app web-only scopes).",
        ),
        (
            "pks.agents.blue_teamer",
            "blueteam_agent",
            "Use for defensive work: detection engineering, IR playbooks, hardening, SOC-style "
            "triage, log/rule tuning, and blue-team exercises.",
        ),
        (
            "pks.agents.bug_bounter",
            "bug_bounter_agent",
            "Use for bug-bounty style hunting: scoped web/API/mobile app testing, PoCs, "
            "responsible disclosure - prefer web pentester only for formal web-app pentest "
            "engagements.",
        ),
        (
            "pks.agents.dfir",
            "dfir_agent",
            "Use for DFIR: disk/memory artifacts, timelines, malware triage in an incident, "
            "evidence handling, and post-breach investigation.",
        ),
        (
            "pks.agents.reverse_engineering_agent",
            "reverse_engineering_agent",
            "Use for static/dynamic RE: binaries, firmware, malware families, unpacking, "
            "and low-level behavior analysis (not generic coding tasks).",
        ),
        (
            "pks.agents.network_traffic_analyzer",
            "network_security_analyzer_agent",
            "Use when the core artifact is network data: PCAP/pcapng, flows, protocols, "
            "packet-level analysis, and traffic baselines.",
        ),
        (
            "pks.agents.wifi_security_tester",
            "wifi_security_agent",
            "Use for wireless-specific work: Wi-Fi assessment, RF/wireless protocols, "
            "and radio-layer security (not general IP pentesting).",
        ),
        (
            "pks.agents.memory_analysis_agent",
            "memory_analysis_agent",
            "Use when the user supplies or discusses memory dumps, process memory, "
            "or runtime-only artifacts (e.g. Volatility-style analysis).",
        ),
        (
            "pks.agents.reporter",
            "reporting_agent",
            "Use for polished deliverables: formal reports, executive summaries, "
            "structured write-ups, and stakeholder-facing documentation.",
        ),
        (
            "pks.agents.ctf_agent",
            "ctf_agent",
            "Use for CTF challenges, flag recovery, challenge artifacts, and iterative CTF solving.",
        ),
        (
            "pks.agents.retester",
            "retester_agent",
            "Use to validate or re-test findings: false-positive reduction, repro checks, "
            "and regression verification after fixes.",
        ),
        (
            "pks.agents.web_pentester",
            "web_pentester_agent",
            "Use for focused web application/API penetration testing and structured "
            "app security assessment (engagement-style), distinct from opportunistic "
            "bounty hunting.",
        ),
        (
            "pks.agents.apt_agent",
            "apt_agent",
            "Use for adversary simulation narratives, targeted campaign-style offensive stories, "
            "and purple/red scenarios where APT framing is explicit (within authorized scope).",
        ),
        (
            "pks.agents.usecase",
            "use_case_agent",
            "Use when the user wants a structured, scenario-driven security walkthrough "
            "or use-case template rather than ad-hoc tooling.",
        ),
        (
            "pks.agents.compliance_agent",
            "compliance_agent",
            "Use for GRC and compliance mapping: NIS2, CRA, ISO 27001, IEC 62443, controls, "
            "evidence packs, and gap analysis (Risk & Compliance specialist).",
        ),
        (
            "pks.agents.codeagent",
            "codeagent",
            "Use for substantial code: multi-file projects, refactors, test harnesses, "
            "and iterative implementation - not quick one-off shell snippets.",
        ),
        (
            "pks.agents.continuous_ops_agent",
            "continuous_ops_agent",
            "Use when the operator wants periodic / long-running monitoring or triage loops "
            "with explicit tick intervals, tmux-friendly background execution, and "
            "API-rate-aware scheduling.",
        ),
    ]


def build_operational_handoffs() -> list:
    """Handoffs to operational specialists (lazy import per module to avoid cycles)."""
    from pks.sdk.agents import Agent as _Agent

    out: list = []
    for mod_path, attr, desc in operational_agent_specs():
        try:
            mod = importlib.import_module(mod_path)
            ag = getattr(mod, attr, None)
            if isinstance(ag, _Agent):
                display = getattr(ag, "name", attr)
                out.append(
                    handoff(
                        ag,
                        tool_description_override=(
                            f"Hand off to {display} for this user request. {desc} "
                            "Provide a concise `task` stating exactly what to do, faithful to "
                            "the user's intent (do not add or drop requirements)."
                        ),
                        on_handoff=_make_on_handoff_task(display),
                        input_type=_HandoffTask,
                        input_filter=handoff_task_filter,
                    )
                )
        except Exception:
            continue
    return out
