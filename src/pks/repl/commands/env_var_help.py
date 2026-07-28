"""
Long-form help for a single environment variable (``/help var NAME``).

Builds on ``ENV_VARS`` / ``EXTRA_ENV_VARS`` plus optional example overrides.
Also owns the shared Rich markup helpers for the parent command (used by
``help.py`` and ``environment_reference.py``).
"""

from __future__ import annotations

from difflib import get_close_matches
from typing import Dict, List, Optional, Tuple

from pks.repl.commands.env_catalog import ENV_VARS
from pks.repl.commands.env_info_catalog import (
    EXTRA_ENV_VARS,
    category_title_for_number,
    constraints_line,
    effective_label,
)

ENV_VAR_DETAIL_COMMAND = "/help"
ENV_VAR_DETAIL_SUBCOMMAND = "var"


def usage_markup_bold() -> str:
    """Rich markup (use literal NAME — avoid angle brackets; Rich treats ``<...>`` as tags)."""
    return f"[bold]{ENV_VAR_DETAIL_COMMAND} {ENV_VAR_DETAIL_SUBCOMMAND} NAME[/bold]"


def example_cyan_line(var_name: str = "PKS_MODEL") -> str:
    """One bullet for docs (PKS green + bold, same as env_var_help snippets)."""
    return (
        f"• [bold #ff3355]{ENV_VAR_DETAIL_COMMAND} {ENV_VAR_DETAIL_SUBCOMMAND} "
        f"{var_name}[/bold #ff3355]"
    )

# Snippets in “How to set” / “Examples” use PKS green + bold (#ff3355), not cyan (reads blue in many themes).

# Extra example lines (shell / REPL) keyed by canonical variable name.
_VAR_EXAMPLES: Dict[str, List[str]] = {
    "PKS_MODEL": [
        "[bold #ff3355]export PKS_MODEL=gpt-5.6-terra[/bold #ff3355]",
        "[bold #ff3355]/env set 9 gpt-4o[/bold #ff3355]",
        "[bold #ff3355]PKS_MODEL=o3-mini pks[/bold #ff3355]  [dim]# one process only[/dim]",
    ],
    "PKS_AGENT_TYPE": [
        "[bold #ff3355]export PKS_AGENT_TYPE=orchestration_agent[/bold #ff3355]  "
        "[dim]# default: breadth-first + specialist tools (parallel / contest / single)[/dim]",
        "[bold #ff3355]export PKS_AGENT_TYPE=root_agent[/bold #ff3355]  [dim]# direct utility execution + specialist routing[/dim]",
        "[bold #ff3355]/agent select redteam_agent[/bold #ff3355]  [dim]# also updates this env[/dim]",
        "[bold #ff3355]/env set 10 ctf_agent[/bold #ff3355]",
    ],
    "PKS_ORCHESTRATION_WORKER_MAX_TURNS": [
        "[bold #ff3355]export PKS_ORCHESTRATION_WORKER_MAX_TURNS=8[/bold #ff3355]  "
        "[dim]# per specialist worker Runner cap (1–32)[/dim]",
        "[bold #ff3355]/env set PKS_ORCHESTRATION_WORKER_MAX_TURNS 4[/bold #ff3355]",
    ],
    "PKS_ORCHESTRATION_MAS_HINT": [
        "[bold #ff3355]export PKS_ORCHESTRATION_MAS_HINT=false[/bold #ff3355]  "
        "[dim]# disable synthetic multi-front nudge for orchestration_agent[/dim]",
        "[bold #ff3355]/env set PKS_ORCHESTRATION_MAS_HINT true[/bold #ff3355]",
    ],
    "PKS_TEMPERATURE": [
        "[bold #ff3355]export PKS_TEMPERATURE=0.3[/bold #ff3355]  [dim]# steadier answers[/dim]",
        "[bold #ff3355]export PKS_TEMPERATURE=1.0[/bold #ff3355]  [dim]# more variety[/dim]",
        "[bold #ff3355]/temperature 0.5[/bold #ff3355]  [dim]# REPL: env + active agent model_settings[/dim]",
        "[bold #ff3355]/env set 11 0.7[/bold #ff3355]",
    ],
    "PKS_TOP_P": [
        "[bold #ff3355]export PKS_TOP_P=0.95[/bold #ff3355]  [dim]# slightly tighter nucleus[/dim]",
        "[bold #ff3355]export PKS_TOP_P=1.0[/bold #ff3355]  [dim]# default, broad sampling[/dim]",
        "[bold #ff3355]/env set 12 1.0[/bold #ff3355]",
    ],
    "PKS_DEBUG": [
        "[bold #ff3355]export PKS_DEBUG=0[/bold #ff3355]  [dim]# quiet[/dim]",
        "[bold #ff3355]export PKS_DEBUG=1[/bold #ff3355]  [dim]# default[/dim]",
        "[bold #ff3355]export PKS_DEBUG=2[/bold #ff3355]  [dim]# tracebacks on errors[/dim]",
        "[bold #ff3355]/env set 13 2[/bold #ff3355]",
    ],
    "PKS_STREAM": [
        "[bold #ff3355]export PKS_STREAM=true[/bold #ff3355]  [dim]# stream LLM tokens[/dim]",
        "[bold #ff3355]/env set 17 true[/bold #ff3355]",
    ],
    "PKS_PARALLEL": [
        "[bold #ff3355]export PKS_PARALLEL=3[/bold #ff3355]",
        "[bold #ff3355]/env set 22 2[/bold #ff3355]",
    ],
    "PKS_MAX_TURNS": [
        "[bold #ff3355]export PKS_MAX_TURNS=50[/bold #ff3355]",
        "[bold #ff3355]export PKS_MAX_TURNS=inf[/bold #ff3355]",
        "[bold #ff3355]/env set 28 100[/bold #ff3355]",
    ],
    "CTF_NAME": [
        "[bold #ff3355]export CTF_NAME=my_challenge_image_tag[/bold #ff3355]  [dim]# pentestperf / pksbench[/dim]",
        "[bold #ff3355]/env set 1 kiddoctf[/bold #ff3355]",
    ],
    "OPENAI_BASE_URL": [
        "[bold #ff3355]export OPENAI_BASE_URL=http://127.0.0.1:20128/v1[/bold #ff3355]",
        "[bold #ff3355]/env set OPENAI_BASE_URL http://127.0.0.1:20128/v1[/bold #ff3355]",
    ],
}

# Optional long “usage notes” prepended after the catalog description (English).
_VAR_NOTES: Dict[str, str] = {
    "PKS_MODEL": (
        "This is the exact model id PKS sends to [bold]OPENAI_BASE_URL[/bold] for most agents "
        "unless overridden by a per-agent [bold]PKS_<AGENT>_MODEL[/bold]."
    ),
    "PKS_AGENT_TYPE": (
        "This is the registered agent key (see [bold]/agent list[/bold]). "
        "[bold]orchestration_agent[/bold] is the usual default: it can delegate with "
        "[bold]run_specialist[/bold], [bold]run_dual_approach_contest[/bold], and "
        "[bold]run_parallel_specialists[/bold], then synthesize for the user; worker subprocess "
        "turn budgets follow [bold]PKS_ORCHESTRATION_WORKER_MAX_TURNS[/bold]. "
        "[bold]root_agent[/bold] handles simple shell/file work directly and routes specialist work. "
        "Pin a specialist when you know exactly which toolkit you need."
    ),
    "PKS_ORCHESTRATION_WORKER_MAX_TURNS": (
        "Applies only to specialist workers spawned by [bold]orchestration_agent[/bold] tools "
        "([bold]run_specialist[/bold], [bold]run_dual_approach_contest[/bold], "
        "[bold]run_parallel_specialists[/bold]); clamped to 1–32."
    ),
    "PKS_ORCHESTRATION_MAS_HINT": (
        "When [bold]true[/bold], [bold]orchestration_agent[/bold] may receive at most one synthetic "
        "English [bold]user[/bold] line per [bold]Runner[/bold] run if the prompt looks multi-front "
        "but only [bold]run_specialist[/bold] ran—suggesting parallel or contest tools. Set "
        "[bold]false[/bold] to disable."
    ),
    "PKS_DEFAULT_AGENT": (
        "Used mainly by the [bold]TUI[/bold] when a new terminal has no agent yet. "
        "The main headless/REPL session still follows [bold]PKS_AGENT_TYPE[/bold]."
    ),
    "OPENAI_BASE_URL": (
        "PKS sends chat-completions requests to this base URL. Use "
        "[bold]https://api.openai.com/v1[/bold] for OpenAI or the [bold]/v1[/bold] base exposed "
        "by your local OpenAI-compatible gateway."
    ),
}


def _all_config_var_names() -> List[str]:
    return [v["name"] for v in ENV_VARS.values()]


def _all_extra_var_names() -> List[str]:
    return [e["name"] for e in EXTRA_ENV_VARS]


def _resolve_name(raw: str) -> Optional[str]:
    """Return canonical env var name or None."""
    key = raw.strip()
    if not key:
        return None
    # Allow accidental $VAR or ${VAR}
    if key.startswith("${") and key.endswith("}"):
        key = key[2:-1]
    if key.startswith("$"):
        key = key[1:]
    upper = key.upper()
    for name in _all_config_var_names():
        if name.upper() == upper:
            return name
    for name in _all_extra_var_names():
        if name.upper() == upper:
            return name
    return None


def _find_config_entry(canonical: str) -> Tuple[Optional[int], Optional[dict]]:
    for num, info in ENV_VARS.items():
        if info["name"] == canonical:
            return int(num), info
    return None, None


def _find_extra_entry(canonical: str) -> Optional[dict]:
    for row in EXTRA_ENV_VARS:
        if row["name"] == canonical:
            return row
    return None


def _default_examples(canonical: str, num: Optional[int], default: Optional[str]) -> List[str]:
    lines: List[str] = [
        f"[bold #ff3355]export {canonical}=<value>[/bold #ff3355]",
    ]
    if num is not None:
        lines.append(f"[bold #ff3355]/env set {num} <value>[/bold #ff3355]")
    lines.append(f"[bold #ff3355]/env set {canonical} <value>[/bold #ff3355]")
    if default is not None and str(default).strip():
        lines.append(f"[dim]# catalog default: {default}[/dim]")
    return lines


def render_variable_help(raw: str) -> Tuple[bool, str, str]:
    """
    Returns (ok, canonical_name, rich_markup_body) for a Panel body.
    """
    canonical = _resolve_name(raw)
    if not canonical:
        names = _all_config_var_names() + _all_extra_var_names()
        by_upper = {n.upper(): n for n in names}
        needle = raw.strip().upper()
        close = get_close_matches(needle, list(by_upper.keys()), n=5, cutoff=0.45)
        suggest = ""
        if close:
            resolved = [by_upper[c] for c in close]
            suggest = "\n[dim]Did you mean: " + ", ".join(resolved) + "?[/dim]"
        return False, raw.strip().upper(), f"[red]Unknown environment variable.[/red]{suggest}"

    num, cfg_entry = _find_config_entry(canonical)
    extra = _find_extra_entry(canonical) if cfg_entry is None else None

    if cfg_entry is not None:
        desc = (cfg_entry.get("description") or "").strip()
        default = cfg_entry.get("default")
        default_s = "—" if default is None else str(default)
        values = constraints_line(canonical, desc)
        when = effective_label(canonical)
        category = category_title_for_number(int(num)) if num is not None else "—"
        lines: List[str] = [
            f"[bold #ff3355]{canonical}[/bold #ff3355]  [dim](/env list #{num})[/dim]",
            f"[dim]Category:[/dim] {category}",
            f"[dim]Values column:[/dim] [bold]{values}[/bold]  ·  [dim]When:[/dim] [bold]{when}[/bold]",
            "",
            "[bold]What it does[/bold]",
            desc,
        ]
        note = _VAR_NOTES.get(canonical)
        if note:
            lines.extend(["", note])
        lines.extend(
            [
                "",
                "[bold]Default in catalog[/bold]",
                default_s,
                "",
                "[bold]How to set[/bold]",
                "• Before launch: shell [bold #ff3355]export[/bold #ff3355] or a line in [bold #ff3355].env[/bold #ff3355] next to the project.",
                "• In session: [bold #ff3355]/env set <#|NAME> <value...>[/bold #ff3355].",
                "• From code: [bold #ff3355]os.environ[\"VAR\"] = \"...\"[/bold #ff3355]",
                "",
                "[bold]Examples[/bold]",
            ]
        )
        for ex in _VAR_EXAMPLES.get(canonical) or _default_examples(canonical, num, default):
            lines.append(f"• {ex}")
        lines.extend(
            [
                "",
                "[dim]Full tables: scroll [bold]/help[/bold] (below the quick guide). Live values: [bold]/env list[/bold].[/dim]",
            ]
        )
        return True, canonical, "\n".join(lines)

    # EXTRA_ENV_VARS only
    assert extra is not None
    desc = (extra.get("description") or "").strip()
    default = extra.get("default", "—")
    values = constraints_line(canonical, desc)
    when = effective_label(canonical)
    lines = [
        f"[bold #ff3355]{canonical}[/bold #ff3355]  [dim](extra — not merged into catalog)[/dim]",
        f"[dim]Values:[/dim] [bold]{values}[/bold]  ·  [dim]When:[/dim] [bold]{when}[/bold]",
        "",
        "[bold]What it does[/bold]",
        desc,
        "",
        "[bold]Default (documentation)[/bold]",
        str(default),
        "",
        "[bold]How to set[/bold]",
        "• [bold #ff3355]export VAR=value[/bold #ff3355] before starting PKS, or edit [bold #ff3355].env[/bold #ff3355].",
        "• If missing from [bold]/env list[/bold], set via shell [bold #ff3355]export[/bold #ff3355] or [bold].env[/bold].",
        "",
        "[bold]Examples[/bold]",
    ]
    for ex in _VAR_EXAMPLES.get(canonical) or [
        f"[bold #ff3355]export {canonical}=<value>[/bold #ff3355]",
    ]:
        lines.append(f"• {ex}")
    lines.append("")
    lines.append(
        "[dim]See [bold]/help[/bold] environment reference if this variable is not in the catalog.[/dim]"
    )
    return True, canonical, "\n".join(lines)
