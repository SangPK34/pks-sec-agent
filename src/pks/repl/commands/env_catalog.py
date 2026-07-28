"""REPL environment catalog: ``ENV_VARS`` and list/get/set/default handlers."""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from rich.box import SIMPLE_HEAD
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from pks.repl.commands.env_catalog_validate import (
    resolve_catalog_spec,
    validate_catalog_value,
)
from pks.repl.commands.env_info_catalog import (
    constraints_line,
    effective_label,
    is_restart_required,
    is_secret,
)
from pks.repl.ui.banner import _PKS_GREEN, _GREY, _quick_guide_subpanel_title

console = Console()

# Same inner table chrome as ``environment_reference._category_vars_table`` (bare /help env tables).
HELP_REFERENCE_MATCH_TABLE_KWARGS: Dict[str, object] = {
    "show_header": True,
    "header_style": "bold white",
    "box": SIMPLE_HEAD,
    "show_edge": False,
    "show_lines": False,
    "pad_edge": False,
    "padding": (0, 1),
    "expand": True,
    "border_style": _PKS_GREEN,
}

# (min_num, max_num) for rows merged from ``EXTRA_ENV_VARS``; set in ``_merge_extra_catalog_entries``.
EXTRA_CATALOG_RANGE: Optional[Tuple[int, int]] = None

# Static rows keep stable numeric IDs; merged ``EXTRA_ENV_VARS`` and dynamic
# per-agent keys append after the highest static ID.
ENV_VARS: Dict[int, Dict[str, object]] = {
    1: {"name": "CTF_NAME", "description": "Name of the CTF challenge to run", "default": None},
    2: {"name": "CTF_CHALLENGE", "description": "Specific challenge name within the CTF", "default": None},
    3: {"name": "CTF_SUBNET", "description": "Network subnet for CTF container", "default": "192.168.3.0/24"},
    4: {"name": "CTF_IP", "description": "IP address for CTF container", "default": "192.168.3.100"},
    5: {"name": "CTF_INSIDE", "description": "Conquer CTF from within container", "default": "true"},
    6: {"name": "CTF_MODEL", "description": "Model override for CTF challenges", "default": None},
    7: {"name": "CTF_CONTAINER_NAME", "description": "Docker container name for CTF", "default": None},
    8: {"name": "CTF_INSTANCE_ID", "description": "Instance ID for CTF tracking", "default": ""},
    9: {"name": "PKS_MODEL", "description": "Model to use for agents", "default": "gpt-5.6-terra"},
    10: {
        "name": "PKS_AGENT_TYPE",
        "description": "Registered agent key (e.g. root_agent, orchestration_agent, redteam_agent)",
        "default": "root_agent",
    },
    11: {
        "name": "PKS_TEMPERATURE",
        "description": "Model temperature (0.0-2.0); REPL /temperature also updates the active agent",
        "default": "0.7",
    },
    12: {"name": "PKS_TOP_P", "description": "Nucleus sampling top_p (0.0-1.0)", "default": "1.0"},
    13: {"name": "PKS_DEBUG", "description": "Debug level (0: tool only, 1: verbose, 2: CLI)", "default": "1"},
    14: {"name": "PKS_BRIEF", "description": "Enable brief output mode", "default": "false"},
    15: {"name": "PKS_STATE", "description": "Enable stateful mode", "default": "false"},
    16: {"name": "PKS_DEFAULT_AGENT", "description": "Default agent type", "default": "redteam_agent"},
    17: {"name": "PKS_STREAM", "description": "Enable LLM inference streaming", "default": "false"},
    18: {"name": "PKS_TOOL_STREAM", "description": "Enable tool output streaming", "default": "true"},
    19: {"name": "PKS_SHOW_CACHE", "description": "Show cache info and message history", "default": "false"},
    20: {"name": "PKS_DEBUG_TOOLS_VIZ", "description": "Debug tool visualization", "default": "false"},
    21: {"name": "PKS_DEBUG_STREAMING", "description": "Debug streaming output", "default": "false"},
    22: {"name": "PKS_PARALLEL", "description": "Number of parallel agents (1-20)", "default": "1"},
    23: {"name": "PKS_PARALLEL_AGENTS", "description": "Comma-separated agent names for parallel", "default": None},
    24: {"name": "PKS_AUTO_RUN_PARALLEL", "description": "Auto-run parallel agents on startup", "default": "false"},
    25: {"name": "PKS_AUTO_RUN_QUEUE", "description": "Auto-run queued commands", "default": "false"},
    26: {"name": "PKS_QUEUE_FILE", "description": "Path to command queue file", "default": None},
    27: {
        "name": "PKS_VERBOSE_LLM_RETRY",
        "description": "Print HTTP/LiteLLM retry and timeout messages to console",
        "default": "false",
    },
    28: {"name": "PKS_MAX_TURNS", "description": "Maximum turns for agent interactions", "default": "inf"},
    29: {"name": "PKS_MAX_INTERACTIONS", "description": "Maximum interactions in session", "default": "inf"},
    31: {"name": "PKS_TOOL_TIMEOUT", "description": "Tool execution timeout (seconds)", "default": None},
    32: {"name": "PKS_IDLE_TIMEOUT", "description": "Idle timeout before cleanup", "default": "100"},
    33: {"name": "PKS_CODE_TIMEOUT", "description": "Code execution timeout", "default": "30"},
    34: {
        "name": "PKS_COMPACTED_MEMORY",
        "description": "Inject /compact conversation summaries into agent system prompts (true/false)",
        "default": "false",
    },
    35: {"name": "PKS_ENV_CONTEXT", "description": "Add environment context to LLM", "default": "true"},
    36: {
        "name": "PKS_TOOL_OUTPUT_MAX",
        "description": "Maximum tool-output characters stored in LLM memory",
        "default": "20000",
    },
    38: {"name": "PKS_WORKSPACE", "description": "Current workspace name", "default": None},
    39: {"name": "PKS_WORKSPACE_DIR", "description": "Workspace directory path", "default": None},
    40: {"name": "PKS_ACTIVE_CONTAINER", "description": "Active Docker container ID", "default": ""},
    41: {"name": "PKS_ACTIVE_CONTAINER_DEFAULT", "description": "Default container", "default": ""},
    42: {"name": "PKS_SUPPORT_MODEL", "description": "Model for support agent", "default": "o3-mini"},
    43: {"name": "PKS_SUPPORT_INTERVAL", "description": "Turns between support executions", "default": "5"},
    44: {"name": "PKS_META_AGENT", "description": "Enable meta agent", "default": "false"},
    45: {"name": "PKS_META_MODEL", "description": "Model for meta agent", "default": None},
    46: {"name": "PKS_META_AUTOCLOSE_GRACE", "description": "Meta agent auto-close grace (s)", "default": "1.5"},
    47: {"name": "PKS_CTR_DIGEST_MODE", "description": "CTR mode: llm or algorithmic", "default": "llm"},
    48: {"name": "PKS_CTR_DIGEST_MODEL", "description": "Model for LLM-based CTR", "default": "gpt-5.6-terra"},
    49: {"name": "PKS_CTR_OUTPUT_DIR", "description": "CTR output directory", "default": None},
    50: {"name": "PKS_CTR_DEFAULT_OUTPUT_DIR", "description": "Default CTR output dir", "default": None},
    51: {"name": "PKS_CTR_DEFAULT_RUN", "description": "Default CTR run identifier", "default": None},
    52: {"name": "PKS_CTR_IS_CTF", "description": "CTR in CTF mode", "default": "false"},
    53: {"name": "PKS_CTR_DISTANCE_HEURISTIC", "description": "CTR graph distance heuristic", "default": None},
    54: {"name": "PKS_GCTR_NITERATIONS", "description": "Tool calls before GCTR analysis", "default": "5"},
    55: {"name": "PKS_TRACING", "description": "Enable OpenTelemetry tracing", "default": "true"},
    56: {"name": "PKS_TELEMETRY", "description": "Enable telemetry collection", "default": "true"},
    57: {"name": "PKS_DISABLE_SESSION_RECORDING", "description": "Disable JSONL recording", "default": "false"},
    59: {"name": "PKS_GUARDRAILS", "description": "Enable security guardrails", "default": "false"},
    60: {"name": "PKS_PLAN", "description": "Enable planning mode", "default": "false"},
    66: {"name": "PKS_REPORT", "description": "Report mode (ctf, nis2, pentesting)", "default": "ctf"},
    67: {"name": "PKS_CONTINUATION_FALLBACK_MODEL", "description": "Fallback model for continuation", "default": None},
    68: {"name": "PKS_API_HOST", "description": "API server host", "default": "127.0.0.1"},
    69: {"name": "PKS_API_PORT", "description": "API server port", "default": "8000"},
    70: {"name": "PKS_API_CORS", "description": "CORS allowed origins", "default": "*"},
    71: {"name": "PKS_API_KEY_HEADER", "description": "API key header name", "default": "X-PKS-API-Key"},
    72: {"name": "PKS_API_LOG_AUTH", "description": "Log authentication", "default": "false"},
    73: {"name": "PKS_API_LOG_REQUESTS", "description": "Log API requests", "default": "false"},
    74: {"name": "PKS_API_LOG_LEVEL", "description": "API log level", "default": "info"},
    75: {"name": "PKS_API_RELOAD", "description": "API hot-reload mode", "default": "false"},
    76: {"name": "PKS_API_WORKERS", "description": "API worker processes", "default": "1"},
    77: {"name": "PKS_AUTH_BASE_URL", "description": "Auth service base URL", "default": None},
    78: {"name": "PKS_AUTH_DEVICE_PORT", "description": "Device auth port", "default": "10101"},
    79: {"name": "PKS_AUTH_PUBLIC_HOST", "description": "Public auth host", "default": None},
    80: {"name": "PKS_AUTH_PUBLIC_PORT", "description": "Public auth port", "default": None},
    81: {"name": "PKS_AUTH_SESSION_TTL_SECONDS", "description": "Session TTL (seconds)", "default": None},
    82: {"name": "PKS_MCP_TOKEN", "description": "MCP authentication token", "default": None},
    83: {"name": "PKS_MCP_AUTH_TOKEN", "description": "MCP auth token (alt)", "default": None},
    84: {"name": "PKS_MCP_SSE_TIMEOUT", "description": "MCP SSE timeout (s)", "default": "5"},
    85: {"name": "PKS_MCP_SSE_READ_TIMEOUT", "description": "MCP SSE read timeout (s)", "default": "300"},
    86: {"name": "PKS_TUI_MODE", "description": "Enable TUI mode", "default": "false"},
    87: {"name": "PKS_TUI_STARTUP_YAML", "description": "TUI startup config YAML", "default": None},
    88: {"name": "PKS_TUI_SHARED_PROMPT", "description": "Shared TUI prompt", "default": None},
    89: {"name": "PKS_TUI_MAX_LINES", "description": "Max TUI output lines", "default": None},
    90: {"name": "PKS_TUI_MAX_RERENDERS_PER_SEC", "description": "Max TUI re-renders/s", "default": None},
    91: {"name": "PKS_VERSION", "description": "PKS version string", "default": "dev"},
    92: {"name": "PKS_THEME", "description": "UI color theme", "default": None},
    93: {"name": "PKS_SKIP_NETWORK_CHECK", "description": "Skip network checks", "default": "false"},
    94: {"name": "PKS_AUTO_COMPACT", "description": "Enable auto-compaction", "default": None},
    95: {
        "name": "PKS_AUTO_COMPACT_THRESHOLD",
        "description": "Context fraction before auto-compact (default 0.8); max 0.8 — higher values are capped",
        "default": None,
    },
    96: {"name": "PKS_WARN_UNATTRIBUTED", "description": "Warn unattributed content", "default": "false"},
    97: {"name": "PKS_UNATTRIBUTED_LOG", "description": "Unattributed content log", "default": "~/.pks_unattributed.log"},
    98: {"name": "PKS_PATTERN_DESCRIPTION", "description": "Agent pattern description", "default": ""},
    99: {"name": "PKS_MODEL_LIST", "description": "Custom model list", "default": None},
    100: {"name": "PKS_CONTEXT_USAGE", "description": "Context usage tracking", "default": None},
    101: {"name": "PKS_SESSION_INPUT_WAIT", "description": "Session input wait (s)", "default": "5.0"},
    102: {"name": "PKS_BROADCAST_MODE", "description": "Broadcast mode for parallel", "default": None},
    103: {
        "name": "PKS_COMPACT_REPL",
        "description": (
            "Enable compact CLI task UI (1/true/yes/on); use 0/false for legacy verbose scrollback. "
            "Locked at startup — restart PKS for the change to take effect."
        ),
        "default": "true",
    },
    104: {
        "name": "PKS_FETCH_ALLOW_INTERNAL",
        "description": (
            "Permit fetch_url to reach loopback/RFC1918/link-local hosts "
            "(true during internal pentests). Cloud-metadata is always blocked."
        ),
        "default": "false",
    },
    105: {
        "name": "PKS_FETCH_USER_AGENT",
        "description": "Override User-Agent for fetch_url (OPSEC).",
        "default": None,
    },
    106: {
        "name": "PKS_FETCH_MAX_BYTES",
        "description": "Hard cap on fetch_url response body (bytes; default 5 MiB).",
        "default": "5242880",
    },
    107: {
        "name": "PKS_FETCH_TIMEOUT",
        "description": "Per-request timeout for fetch_url (seconds).",
        "default": "20",
    },
    108: {
        "name": "PKS_REASONING_EFFORT",
        "description": "Reasoning level: off, low, medium, high, xhigh, or max",
        "default": None,
    },
    109: {
        "name": "PKS_MODEL_MAX_INPUT_TOKENS",
        "description": "Override the selected model context-window size",
        "default": None,
    },
}


def _catalog_default_from_extra(entry: Dict[str, object]) -> Optional[str]:
    raw = entry.get("default")
    if raw is None:
        return None
    s = str(raw).strip()
    sl = s.lower()
    if sl in ("unset", "unset (off)", "—", "-", ""):
        return None
    return s


def _merge_extra_catalog_entries() -> None:
    """Append ``env_info_catalog.EXTRA_ENV_VARS`` into ``ENV_VARS`` (same keys as /help reference)."""
    global EXTRA_CATALOG_RANGE  # pylint: disable=global-statement

    from pks.repl.commands.env_info_catalog import EXTRA_ENV_VARS

    existing = {str(v["name"]) for v in ENV_VARS.values()}
    n = max(ENV_VARS.keys()) + 1
    first = n
    for entry in EXTRA_ENV_VARS:
        name = str(entry["name"])
        if name in existing:
            continue
        ENV_VARS[n] = {
            "name": name,
            "description": str(entry.get("description") or ""),
            "default": _catalog_default_from_extra(entry),
        }
        existing.add(name)
        n += 1
    last = n - 1
    if last >= first:
        EXTRA_CATALOG_RANGE = (first, last)


def get_env_var_value(var_name: str) -> str:
    """Return current value or catalog default (or ``Not set``)."""
    for var_info in ENV_VARS.values():
        if var_info["name"] == var_name:
            return os.environ.get(var_name, var_info["default"] or "Not set")
    return "Unknown variable"


def set_env_var(var_name: str, value: str) -> bool:
    os.environ[var_name] = value
    return True


def find_var_num_by_name(var_name: str) -> Optional[int]:
    for num, var_info in ENV_VARS.items():
        if var_info["name"] == var_name:
            return num
    return None


def add_agent_model_vars_to_catalog() -> None:
    """Append PKS_<AGENT>_MODEL entries (and parallel instances) to ENV_VARS."""
    try:
        from pks.agents import get_available_agents

        available_agents = get_available_agents()
        current_var_num = max(ENV_VARS.keys()) + 1

        for agent_key in sorted(available_agents.keys()):
            var_name = f"PKS_{agent_key.upper()}_MODEL"
            agent_obj = available_agents[agent_key]
            agent_display_name = getattr(agent_obj, "name", agent_key)

            ENV_VARS[current_var_num] = {
                "name": var_name,
                "description": f"Model override for {agent_display_name} agent",
                "default": None,
            }
            current_var_num += 1

        parallel_count = int(os.getenv("PKS_PARALLEL", "1"))
        if parallel_count > 1:
            for agent_key in sorted(available_agents.keys()):
                agent_obj = available_agents[agent_key]
                agent_display_name = getattr(agent_obj, "name", agent_key)

                for instance_num in range(1, parallel_count + 1):
                    var_name = f"PKS_{agent_key.upper()}_{instance_num}_MODEL"

                    ENV_VARS[current_var_num] = {
                        "name": var_name,
                        "description": (
                            f"Model override for {agent_display_name} instance #{instance_num}"
                        ),
                        "default": None,
                    }
                    current_var_num += 1
    except Exception:  # pylint: disable=broad-except
        pass


def mask_secret_catalog_display(key: str, value: str) -> str:
    if any(s in key.lower() for s in ("key", "token", "secret", "password")):
        if not value:
            return value
        half = len(value) // 2
        return value[:half] + "*" * (len(value) - half)
    return value


def print_bare_env_session_view() -> bool:
    """``/env`` with no args: only ``PKS_*`` / ``CTF_*`` keys present in ``os.environ`` (legacy behaviour)."""
    env_vars = {k: v for k, v in os.environ.items() if k.startswith(("PKS_", "CTF_"))}

    if not env_vars:
        console.print(
            Panel(
                Text("No PKS_ or CTF_ environment variables in this process.", style="yellow"),
                title=_quick_guide_subpanel_title("Environment variables — session"),
                title_align="left",
                border_style=_PKS_GREEN,
                padding=(1, 1),
            )
        )
        return True

    table = Table(**HELP_REFERENCE_MATCH_TABLE_KWARGS)
    table.add_column("Variable", no_wrap=True, min_width=18)
    table.add_column("Value", ratio=1)

    for idx, (key, value) in enumerate(sorted(env_vars.items())):
        body_style = "white" if idx % 2 == 0 else _GREY
        masked = mask_secret_catalog_display(key, value)
        table.add_row(
            Text(key, style=f"bold {_PKS_GREEN}"),
            Text(masked, style=body_style),
        )

    console.print(
        Panel(
            table,
            title=_quick_guide_subpanel_title("Environment variables — session"),
            title_align="left",
            border_style=_PKS_GREEN,
            padding=(1, 1),
        )
    )
    console.print(
        "[dim]Tip: [bold]/env list[/bold] for the full numbered catalog (all variables).[/dim]"
    )
    return True


def handle_env_catalog_list(_: Optional[List[str]] = None) -> bool:
    """Print every catalog row; table chrome matches ``/help`` environment reference tables."""
    table = Table(**HELP_REFERENCE_MATCH_TABLE_KWARGS)
    table.add_column("#", justify="right", width=4, no_wrap=True)
    table.add_column("Variable", no_wrap=True, min_width=16)
    table.add_column("Current", min_width=8, ratio=1)
    table.add_column("Default", min_width=8, max_width=22, no_wrap=True)
    table.add_column("Values", min_width=10, ratio=2)
    table.add_column("When", min_width=8, no_wrap=True, ratio=1)
    table.add_column("Description", min_width=18, ratio=4)

    for idx, (num, var_info) in enumerate(sorted(ENV_VARS.items(), key=lambda x: x[0])):
        name = str(var_info["name"])
        desc = str(var_info.get("description") or "")
        default = var_info.get("default")
        default_s = "—" if default is None else str(default)
        raw_val = get_env_var_value(name)
        current_value = mask_secret_catalog_display(name, raw_val)
        body_style = "white" if idx % 2 == 0 else _GREY
        table.add_row(
            Text(str(num), style=body_style),
            Text(name, style=f"bold {_PKS_GREEN}"),
            Text(current_value, style=body_style),
            Text(default_s, style=_PKS_GREEN),
            Text(constraints_line(name, desc), style=body_style),
            Text(effective_label(name), style=body_style),
            Text(desc, style=body_style),
        )

    console.print(
        Panel(
            table,
            title=_quick_guide_subpanel_title("Environment variables — catalog (all)"),
            title_align="left",
            border_style=_PKS_GREEN,
            padding=(1, 1),
        )
    )
    console.print(
        "\n[#9aa0a6][PKS] Usage:[/] "
        "[bold #ff3355]/env set <#|NAME> <value...>[/bold #ff3355] — "
        "value may contain spaces (no quotes). "
        "[bold #ff3355]/env default[/bold #ff3355] restores catalog defaults."
    )
    return True


def handle_env_catalog_get(args: Optional[List[str]] = None) -> bool:
    if not args or not str(args[0]).strip():
        console.print("[yellow]Usage: /env get <number|VARIABLE_NAME>[/yellow]")
        return False

    resolved = resolve_catalog_spec(str(args[0]), ENV_VARS)
    if not resolved:
        console.print(f"[red]Error: Unknown catalog entry '{args[0]}'[/red]")
        console.print("[yellow]Use /env list for numbers and names.[/yellow]")
        return False

    var_num, var_info, var_name = resolved
    raw_val = get_env_var_value(var_name)
    current_value = mask_secret_catalog_display(var_name, raw_val)
    def_disp = var_info["default"] if var_info["default"] is not None else "Not set"
    desc = str(var_info.get("description") or "")

    body = (
        f"[bold #ff3355]{var_name}[/bold #ff3355]  [dim](#{var_num})[/dim]\n\n"
        f"[#9aa0a6]Current:[/] [white]{current_value}[/white]\n"
        f"[#9aa0a6]Default:[/] [white]{def_disp}[/white]\n\n"
        f"[dim]{desc}[/dim]"
    )
    console.print(
        Panel(
            body,
            title="[bold #ff3355]Catalog variable[/bold #ff3355]",
            title_align="left",
            border_style="#ff3355",
            padding=(1, 1),
        )
    )
    return True


def handle_env_catalog_set(args: Optional[List[str]] = None) -> bool:
    if not args or len(args) < 2:
        console.print("[yellow]Usage: /env set <number|VARIABLE_NAME> <value...>[/yellow]")
        return False

    resolved = resolve_catalog_spec(str(args[0]), ENV_VARS)
    if not resolved:
        console.print(f"[red]Error: Unknown catalog entry '{args[0]}'[/red]")
        console.print("[yellow]Use /env list for numbers and names.[/yellow]")
        return False

    value = " ".join(args[1:]).strip()
    if not value:
        console.print("[red]Error: value cannot be empty.[/red]")
        return False

    _var_num, var_info, var_name = resolved
    if is_restart_required(var_name):
        console.print(
            f"[red]Error: [bold #ff3355]{var_name}[/bold #ff3355] is locked at "
            f"startup; runtime mutation has no effect.[/red]"
        )
        console.print(
            f"[yellow]Export it before launching pks, e.g. "
            f"[white]export {var_name}={value}[/white], or add it to your .env "
            f"and restart.[/yellow]"
        )
        return False

    err = validate_catalog_value(var_name, value, var_info)
    if err:
        console.print(f"[red]{err}[/red]")
        return False

    old_value = get_env_var_value(var_name)
    set_env_var(var_name, value)

    console.print(
        f"Set [bold #ff3355]{var_name}[/bold #ff3355] to "
        f"[white]'{value}'[/white] [dim](was: '{old_value}')[/dim]"
    )
    return True


def handle_env_catalog_default(args: Optional[List[str]] = None) -> bool:
    if args:
        console.print("[yellow]Usage: /env default[/yellow] (no arguments)")
        return False

    skipped: List[str] = []
    preserved_secrets: List[str] = []
    for _num, var_info in sorted(ENV_VARS.items()):
        name = str(var_info["name"])
        if is_restart_required(name):
            skipped.append(name)
            continue
        if is_secret(name):
            preserved_secrets.append(name)
            continue
        default = var_info["default"]
        if default is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = str(default)

    console.print(
        "Restored runtime [bold #ff3355]catalog[/bold #ff3355] variables "
        "to their registered defaults."
    )
    if preserved_secrets:
        console.print(
            f"[yellow]Preserved {len(preserved_secrets)} credential variable(s) "
            f"to keep authentication intact: {', '.join(preserved_secrets)}. "
            f"Use [white]/env set <NAME> <value>[/white] to mutate them explicitly.[/yellow]"
        )
    if skipped:
        console.print(
            f"[yellow]Skipped {len(skipped)} locked-at-startup variable(s); "
            f"restart pks (or export them) to reset: {', '.join(skipped)}.[/yellow]"
        )
    return True


_merge_extra_catalog_entries()
add_agent_model_vars_to_catalog()
