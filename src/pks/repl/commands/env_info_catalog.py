"""
Metadata for the environment reference (tables under ``/help``; detail via ``/help var NAME``): when each
variable takes effect, value constraints, and extras.

Descriptions in ``env_catalog.ENV_VARS`` are the short summaries; this module adds
English guidance on runtime vs restart and allowed shapes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Map ENV_VARS numeric key ranges to section titles (must match env_catalog.py groupings).
_CATEGORY_BY_NUM: List[Tuple[int, Optional[int], str]] = [
    (1, 8, "CTF (capture-the-flag)"),
    (9, 16, "Core agent & model"),
    (17, 21, "Streaming & debug output"),
    (22, 27, "Parallelization & queue"),
    (28, 33, "Execution limits & timeouts"),
    (34, 37, "Memory & context"),
    (38, 41, "Workspace & containers"),
    (42, 46, "Support & meta agent"),
    (47, 54, "CTR / G-CTR"),
    (55, 57, "Tracing & telemetry"),
    (59, 60, "Security & planning"),
    (66, 67, "Reporting & continuation"),
    (68, 76, "HTTP API server"),
    (77, 81, "Authentication service"),
    (82, 85, "MCP (Model Context Protocol)"),
    (86, 90, "TUI"),
    (91, 109, "Advanced / misc"),
]

# English blurbs and optional dependency rules for environment reference category panels.
# dependency_id is resolved in repl.commands.environment_reference (pentestperf = pks.pksbench importable).
CATEGORY_DISPLAY: Dict[str, Dict[str, Any]] = {
    "Core agent & model": {
        "overview": "[dim]Defaults for which [bold]model[/bold] and [bold]agent type[/bold] run ([bold]root_agent[/bold] when unset, or e.g. orchestration_agent, redteam_agent, ctf_agent), optional [bold]PKS_ORCHESTRATION_*[/bold] tuning when the entry agent spawns specialist workers, sampling (temperature / top_p), debug verbosity, and output shaping. These affect most interactive and headless sessions.[/dim]",
    },
    "CTF (capture-the-flag)": {
        "overview": "[dim]Docker-backed benchmark challenges (pentestperf-style images): challenge selection, container networking, and whether tools execute inside the target.[/dim]",
        "dependency_id": "pentestperf",
        "missing_dependency_note": (
            "[#9aa0a6]The [bold]pksbench[/bold] package ([bold]pks.pksbench[/bold]) is not available in this environment. "
            "The published wheel often excludes [bold]src/pks/pksbench/[/bold] (see [bold]pyproject.toml[/bold] hatch excludes); "
            "install from a [bold]full source[/bold] tree with [bold]pip install -e .[/bold], or use a build that ships pksbench. "
            "You also need [bold]Docker[/bold] for challenge containers. "
            "Until then, [bold]CTF_*[/bold] variables have no effect here—the table is omitted. "
            "They remain documented for CI/benchmark installs.[/]"
        ),
        "present_dependency_note": (
            "[#9aa0a6][bold]pksbench[/bold] is loaded. If you do not run CTF or benchmark flows, consider a minimal PKS install "
            "(wheel without pksbench) so [bold]CTF_*[/bold] stay inert and the attack surface stays smaller.[/]"
        ),
        "omit_table_without_dependency": True,
    },
    "Streaming & debug output": {
        "overview": "[dim]Control LLM and tool streaming to the terminal, cache visibility, and low-level debug flags for tools and context.[/dim]",
    },
    "Parallelization & queue": {
        "overview": "[dim]Parallel agent workers, auto-run behaviour, and queued command files for batch or multi-terminal setups.[/dim]",
    },
    "Execution limits & timeouts": {
        "overview": "[dim]Turn and interaction caps plus timeouts for tools, idle sessions, and code execution.[/dim]",
    },
    "Memory & context": {
        "overview": "[dim]Optional memory backends (episodic/semantic), context truncation, and how much tool output is shown.[/dim]",
    },
    "Workspace & containers": {
        "overview": "[dim]Named workspace, directories on disk, and which Docker container is considered active for tools.[/dim]",
    },
    "Support & meta agent": {
        "overview": "[dim]Background support and meta agents: models, intervals, and auto-close timing.[/dim]",
    },
    "CTR / G-CTR": {
        "overview": "[dim]Control-the-Rope style digest pipelines: modes, models, output paths, and G-CTR iteration counts.[/dim]",
    },
    "Tracing & telemetry": {
        "overview": "[dim]OpenTelemetry tracing, product telemetry, and session-recording controls.[/dim]",
    },
    "Security & planning": {
        "overview": "[dim]Guardrails and planning-mode toggles for safer or more structured agent behaviour.[/dim]",
    },
    "Reporting & continuation": {
        "overview": "[dim]Report mode presets and fallback models when continuation needs a different endpoint.[/dim]",
    },
    "HTTP API server": {
        "overview": "[dim]Optional HTTP API: bind address, CORS, logging, workers, reload, and auth header naming.[/dim]",
    },
    "Authentication service": {
        "overview": "[dim]Device / OAuth-style auth helper: base URL, public host and ports, session TTL.[/dim]",
    },
    "MCP (Model Context Protocol)": {
        "overview": "[dim]MCP server tokens and SSE timeouts for Model Context Protocol integrations.[/dim]",
    },
    "TUI": {
        "overview": "[dim]Textual UI: enablement, startup YAML, shared prompt, scrollback and render throttling.[/dim]",
    },
    "Advanced / misc": {
        "overview": "[dim]Version string, themes, network checks, auto-compaction thresholds, patterns, and other advanced knobs.[/dim]",
    },
    "Provider keys & runtime": {
        "overview": "[dim]Provider API keys and bases, Ollama routing, parallel merge digests, sensitive-command guards, and other runtime toggles merged from the former “Additional” reference.[/dim]",
    },
    "Per-agent model overrides": {
        "overview": "[dim]Per-agent model overrides generated from registered agents (and per-instance slots when running more than one parallel worker).[/dim]",
    },
}


def category_title_for_number(num: int) -> str:
    try:
        from pks.repl.commands import env_catalog as _ec

        r = _ec.EXTRA_CATALOG_RANGE
        if r and r[0] <= num <= r[1]:
            return "Provider keys & runtime"
    except Exception:  # pylint: disable=broad-except
        pass
    for lo, hi, title in _CATEGORY_BY_NUM:
        if hi is not None and lo <= num <= hi:
            return title
        if hi is None and num >= lo:
            return title
    return "Per-agent model overrides"


# Subsystems that typically read these only once per process or TUI session.
_RESTART_RECOMMENDED = frozenset(
    {
        "PKS_TUI_MODE",
        "PKS_TUI",
        "PKS_TUI_STARTUP_YAML",
        "PKS_TUI_SHARED_PROMPT",
        "PKS_TUI_MAX_LINES",
        "PKS_TUI_MAX_RERENDERS_PER_SEC",
        "PKS_THEME",
        "PKS_API_HOST",
        "PKS_API_PORT",
        "PKS_API_WORKERS",
        "PKS_API_RELOAD",
        "PKS_API_CORS",
        "PKS_TRACING",
        "PKS_TELEMETRY",
        "PKS_VERSION",
        "PKS_AUTO_UPDATE",
        "PKS_COMPACT_REPL",
    }
)

# Often read from os.environ on each tool / stream invocation.
_RUNTIME_FRIENDLY = frozenset(
    {
        "PKS_STREAM",
        "PKS_TOOL_STREAM",
        "PKS_SHOW_CACHE",
        "PKS_DEBUG_TOOLS_VIZ",
        "PKS_DEBUG_STREAMING",
        "PKS_VERBOSE_LLM_RETRY",
        "PKS_HTTP_ERROR_BODY",
        "PKS_TOOL_TIMEOUT",
        "PKS_TOOL_OUTPUT_MAX",
        "PKS_REASONING_EFFORT",
        "PKS_MODEL_MAX_INPUT_TOKENS",
        "PKS_GUARDRAILS",
        "PKS_PLAN",
        "PKS_SENSITIVE_GUARD",
        "PKS_AVOID_SUDO",
        "PKS_YOLO",
        "PKS_UNRESTRICTED",
        "PKS_UNRESTRICTED_LOG",
        "PKS_DISABLE_TOOL_WAIT_HINTS",
        "PKS_TOOL_OUTPUT_MARKDOWN",
        "PKS_PATTERN_DESCRIPTION",
        "PKS_PARALLEL_EXEC_MODE",
        "PKS_PARALLEL_EXTERNAL_TIMEOUT",
        "PKS_TASK_RESET_PENDING",
        "PKS_SKIP_UPDATE_CHECK",
        "PKS_ACTIVE_COMMAND_TERMINAL",
        "PKS_MERGE_SUMMARIZE_PER_WORKER",
        "PKS_MERGE_SUMMARIZE_MIN_MESSAGES",
        "SSH_USER",
        "SSH_HOST",
    }
)


def effective_label(var_name: str) -> str:
    """Single-word timing label; details are in INTRO_MARKUP *When changes apply*."""
    if var_name in _RESTART_RECOMMENDED:
        return "Restart"
    if var_name in _RUNTIME_FRIENDLY:
        return "Runtime"
    if var_name.startswith("PKS_") and var_name.endswith("_MODEL"):
        return "Mixed"
    return "Mixed"


def is_restart_required(var_name: str) -> bool:
    """True when ``var_name`` is read once at startup; runtime mutation is a no-op.

    Consumers (e.g. ``/env set`` / ``/env default``) should refuse to mutate
    these variables and instruct the user to export them before launching PKS.
    """
    return var_name in _RESTART_RECOMMENDED


def is_secret(var_name: str) -> bool:
    """True when the variable holds a credential (constraint label ``secret``).

    ``/env default`` must refuse to mutate these — popping them from ``os.environ``
    silently breaks authentication (OPENAI_API_KEY, PKS_MCP_TOKEN,
    PKS_MCP_AUTH_TOKEN) and the user has no in-session way to
    restore them.
    """
    return _CONSTRAINT_LABEL_BY_VAR.get(var_name) == "secret"


# Per-variable type/range for environment reference tables (intro explains bool, string, int, float, etc.).
_CONSTRAINT_LABEL_BY_VAR: Dict[str, str] = {
    "CTF_NAME": "string",
    "CTF_CHALLENGE": "string",
    "CTF_SUBNET": "string",
    "CTF_IP": "string",
    "CTF_INSIDE": "bool",
    "CTF_MODEL": "string",
    "CTF_CONTAINER_NAME": "string",
    "CTF_INSTANCE_ID": "string",
    "PKS_MODEL": "string",
    "PKS_AGENT_TYPE": "string",
    "PKS_TEMPERATURE": "float 0.0–2.0",
    "PKS_TOP_P": "float 0.0–1.0",
    "PKS_DEBUG": "int 0–2",
    "PKS_BRIEF": "bool",
    "PKS_STATE": "bool",
    "PKS_DEFAULT_AGENT": "string",
    "PKS_STREAM": "bool",
    "PKS_TOOL_STREAM": "bool",
    "PKS_SHOW_CACHE": "bool",
    "PKS_DEBUG_TOOLS_VIZ": "bool",
    "PKS_DEBUG_STREAMING": "bool",
    "PKS_COMPACT_REPL": "bool",
    "PKS_PARALLEL": "int 1–20",
    "PKS_PARALLEL_AGENTS": "string",
    "PKS_AUTO_RUN_PARALLEL": "bool",
    "PKS_AUTO_RUN_QUEUE": "bool",
    "PKS_QUEUE_FILE": "string",
    "PKS_VERBOSE_LLM_RETRY": "bool",
    "PKS_MAX_TURNS": "int ≥1",
    "PKS_ORCHESTRATION_WORKER_MAX_TURNS": "int 1–32",
    "PKS_ORCHESTRATION_MAS_HINT": "bool",
    "PKS_MAX_INTERACTIONS": "int ≥1",
    "PKS_TOOL_TIMEOUT": "int (s)",
    "PKS_IDLE_TIMEOUT": "int (s)",
    "PKS_CODE_TIMEOUT": "int (s)",
    "PKS_COMPACTED_MEMORY": "bool",
    "PKS_ENV_CONTEXT": "bool",
    "PKS_TOOL_OUTPUT_MAX": "int ≥800",
    "PKS_REASONING_EFFORT": "off|low|medium|high|xhigh|max",
    "PKS_MODEL_MAX_INPUT_TOKENS": "int ≥8000",
    "PKS_WORKSPACE": "string",
    "PKS_WORKSPACE_DIR": "string",
    "PKS_ACTIVE_CONTAINER": "string",
    "PKS_ACTIVE_CONTAINER_DEFAULT": "string",
    "PKS_SUPPORT_MODEL": "string",
    "PKS_SUPPORT_INTERVAL": "int",
    "PKS_META_AGENT": "bool",
    "PKS_META_MODEL": "string",
    "PKS_META_AUTOCLOSE_GRACE": "float (s)",
    "PKS_CTR_DIGEST_MODE": "string",
    "PKS_CTR_DIGEST_MODEL": "string",
    "PKS_CTR_OUTPUT_DIR": "string",
    "PKS_CTR_DEFAULT_OUTPUT_DIR": "string",
    "PKS_CTR_DEFAULT_RUN": "string",
    "PKS_CTR_IS_CTF": "bool",
    "PKS_CTR_DISTANCE_HEURISTIC": "string",
    "PKS_GCTR_NITERATIONS": "int",
    "PKS_TRACING": "bool",
    "PKS_TELEMETRY": "bool",
    "PKS_DISABLE_SESSION_RECORDING": "bool",
    "PKS_GUARDRAILS": "bool",
    "PKS_PLAN": "bool",
    "PKS_REPORT": "string",
    "PKS_CONTINUATION_FALLBACK_MODEL": "string",
    "PKS_API_HOST": "string",
    "PKS_API_PORT": "int",
    "PKS_API_CORS": "string",
    "PKS_API_KEY_HEADER": "string",
    "PKS_API_LOG_AUTH": "bool",
    "PKS_API_LOG_REQUESTS": "bool",
    "PKS_API_LOG_LEVEL": "string",
    "PKS_API_RELOAD": "bool",
    "PKS_API_WORKERS": "int",
    "PKS_AUTH_BASE_URL": "string",
    "PKS_AUTH_DEVICE_PORT": "int",
    "PKS_AUTH_PUBLIC_HOST": "string",
    "PKS_AUTH_PUBLIC_PORT": "int",
    "PKS_AUTH_SESSION_TTL_SECONDS": "int (s)",
    "PKS_MCP_TOKEN": "secret",
    "PKS_MCP_AUTH_TOKEN": "secret",
    "PKS_MCP_SSE_TIMEOUT": "int (s)",
    "PKS_MCP_SSE_READ_TIMEOUT": "int (s)",
    "PKS_TUI_MODE": "bool",
    "PKS_TUI_STARTUP_YAML": "string",
    "PKS_TUI_SHARED_PROMPT": "string",
    "PKS_TUI_MAX_LINES": "int",
    "PKS_TUI_MAX_RERENDERS_PER_SEC": "int",
    "PKS_VERSION": "string",
    "PKS_THEME": "string",
    "PKS_SKIP_NETWORK_CHECK": "bool",
    "PKS_AUTO_COMPACT": "bool",
    "PKS_AUTO_COMPACT_THRESHOLD": "float 0.0–0.8",
    "PKS_WARN_UNATTRIBUTED": "bool",
    "PKS_UNATTRIBUTED_LOG": "string",
    "PKS_PATTERN_DESCRIPTION": "string",
    "PKS_MODEL_LIST": "string",
    "PKS_CONTEXT_USAGE": "string",
    "PKS_SESSION_INPUT_WAIT": "float (s)",
    "PKS_BROADCAST_MODE": "string",
    "PKS_MERGE_SUMMARIZE_PER_WORKER": "int 0–1",
    "PKS_MERGE_SUMMARIZE_MIN_MESSAGES": "int ≥1",
    "PKS_RATE_TIER": "string",
    "PKS_YOLO": "bool",
    "PKS_SENSITIVE_GUARD": "bool",
    "PKS_UNRESTRICTED": "bool",
    "PKS_UNRESTRICTED_LOG": "bool",
    "PKS_DISABLE_TOOL_WAIT_HINTS": "bool",
    "PKS_TOOL_OUTPUT_MARKDOWN": "bool",
    "PKS_PARALLEL_EXEC_MODE": "string",
    "PKS_PARALLEL_EXTERNAL_TIMEOUT": "float (s)",
    "PKS_TASK_RESET_PENDING": "int 0–1",
    "PKS_SKIP_UPDATE_CHECK": "bool",
    "PKS_AUTO_UPDATE": "bool",
    "PKS_ACTIVE_COMMAND_TERMINAL": "string",
    "PKS_VERBOSE_HTTP_RETRY": "bool",
    "PKS_HTTP_ERROR_BODY": "bool",
    "OPENAI_API_KEY": "secret",
    "OPENAI_BASE_URL": "string (URL)",
}


def constraints_line(var_name: str, description: str) -> str:
    """Compact type (and range if needed) for env reference tables; see INTRO_MARKUP for full semantics."""
    _ = description  # reserved if we add heuristics for unknown vars later
    return _CONSTRAINT_LABEL_BY_VAR.get(var_name, "string")


# Merged into ``env_catalog.ENV_VARS`` at import time. ``constraints``/``effective`` come
# from ``_CONSTRAINT_LABEL_BY_VAR`` and ``_RESTART_RECOMMENDED``/``_RUNTIME_FRIENDLY`` above
# (single source of truth; use ``constraints_line`` / ``effective_label`` to read them).
EXTRA_ENV_VARS: List[Dict[str, Any]] = [
    {
        "name": "PKS_ORCHESTRATION_WORKER_MAX_TURNS",
        "default": "6",
        "description": (
            "Max Runner turns per specialist worker spawned by orchestration_agent tools "
            "(run_specialist, run_dual_approach_contest, run_parallel_specialists). Clamped 1–32."
        ),
    },
    {
        "name": "PKS_ORCHESTRATION_MAS_HINT",
        "default": "true",
        "description": (
            "When true, orchestration_agent may receive one synthetic user-line nudge per Runner "
            "run if the user message looks multi-front but only run_specialist was used—suggesting "
            "parallel or contest tools."
        ),
    },
    {
        "name": "PKS_MERGE_SUMMARIZE_PER_WORKER",
        "default": "1",
        "description": "When 1, enable per-worker merge digests in parallel multi-agent flows.",
    },
    {
        "name": "PKS_MERGE_SUMMARIZE_MIN_MESSAGES",
        "default": "20",
        "description": "Minimum messages in a worker before per-worker digest runs (when merge per worker is on).",
    },
    {
        "name": "PKS_RATE_TIER",
        "default": "pro",
        "description": "Continuous-ops pacing profile: pro or edu.",
    },
    {
        "name": "PKS_YOLO",
        "default": "unset (off)",
        "description": "When true, skips interactive sensitive-command approval (equivalent to CLI --yolo). Unsafe on untrusted prompts.",
    },
    {
        "name": "PKS_AVOID_SUDO",
        "default": "unset (off)",
        "description": "When true, never run sudo/su/pkexec/doas via generic_linux_command (hard block even with YOLO) and add a system-prompt policy to prefer non-privileged alternatives.",
    },
    {
        "name": "PKS_SENSITIVE_GUARD",
        "default": "true",
        "description": "Master switch for sensitive-command detection in CLI headless mode. Set to false to disable prompts (still prefer PKS_YOLO only when you understand the risk). Prompts are interactive and need a real TTY after streaming output; use YOLO or automation only when you accept non-interactive runs.",
    },
    {
        "name": "PKS_UNRESTRICTED",
        "default": "false",
        "description": "Relaxes some logging / content filters in model paths (developer-oriented).",
    },
    {
        "name": "PKS_UNRESTRICTED_LOG",
        "default": "unset",
        "description": "Additional logging when PKS_UNRESTRICTED is active.",
    },
    {
        "name": "PKS_DISABLE_TOOL_WAIT_HINTS",
        "default": "unset (off)",
        "description": "Disables tool-batch wait hints (Result-rail messages and footer updates).",
    },
    {
        "name": "PKS_TOOL_OUTPUT_MARKDOWN",
        "default": "true",
        "description": "Render markdown-like tool stdout under Result/captured when heuristics match.",
    },
    {
        "name": "PKS_PARALLEL_EXEC_MODE",
        "default": "external",
        "description": "How parallel agent workers are launched (e.g. external terminals vs embedded).",
    },
    {
        "name": "PKS_PARALLEL_EXTERNAL_TIMEOUT",
        "default": "900",
        "description": "Seconds to wait for external parallel workers.",
    },
    {
        "name": "PKS_TASK_RESET_PENDING",
        "default": "unset",
        "description": "Internal flag used by the headless loop for task-reset signalling.",
    },
    {
        "name": "PKS_SKIP_UPDATE_CHECK",
        "default": "unset",
        "description": "Skip startup update / connectivity checks.",
    },
    {
        "name": "PKS_AUTO_UPDATE",
        "default": "unset (off)",
        "description": "When true and this variable is present in the environment, install pks-framework updates at startup (or with pks --update) without prompting. Unset = always ask.",
    },
    {
        "name": "PKS_ACTIVE_COMMAND_TERMINAL",
        "default": "unset",
        "description": "Tracks which command terminal is active in multi-terminal flows.",
    },
    {
        "name": "PKS_VERBOSE_HTTP_RETRY",
        "default": "unset",
        "description": "Alias accepted by HTTP client; same idea as PKS_VERBOSE_LLM_RETRY.",
    },
    {
        "name": "PKS_HTTP_ERROR_BODY",
        "default": "unset",
        "description": "Include HTTP error bodies in verbose retry / debug output.",
    },
    {
        "name": "OPENAI_API_KEY",
        "default": "unset",
        "description": "API key sent to the configured OpenAI-compatible endpoint.",
    },
    {
        "name": "OPENAI_BASE_URL",
        "default": "https://api.openai.com/v1",
        "description": "Base URL for OpenAI or an OpenAI-compatible local gateway.",
    },
]

INTRO_MARKUP = """Variables are normal [bold #ff3355]process environment[/bold #ff3355] values. PKS also loads a project [bold #ff3355].env[/bold #ff3355] file when present.

[bold]How to set them[/bold]
• [dim white]Before launch:[/dim white] [bold #ff3355]export VAR=value[/bold #ff3355] in your shell, or add a line to [bold #ff3355].env[/bold #ff3355], then start PKS.
• [dim white]During a session:[/dim white] [bold #ff3355]/env set <#|NAME> <value...>[/bold #ff3355], or Python [bold #ff3355]os.environ["VAR"]="value"[/bold #ff3355] from extensions.

[bold]When changes apply[/bold]
• [italic]Runtime[/italic] — code that calls [bold]os.getenv[/bold] on each use picks up new values immediately (streaming flags, many tool options, debug toggles).
• [italic]Restart / new session[/italic] — TUI mode, API worker count, some telemetry switches, or anything read only at process startup. In tables this appears as [bold]Restart[/bold].
• [italic]Mixed[/italic] — values are in [bold]os.environ[/bold], but parts of PKS cache a [bold]PKSConfig[/bold] snapshot or model client until you start a new inference turn, switch agents with [bold]/agent[/bold], or restart. When in doubt, restart PKS after changing core model or agent settings.

The [italic]When[/italic] column uses only [bold]Runtime[/bold], [bold]Restart[/bold], or [bold]Mixed[/bold], matching the three categories above.

[bold]Allowed value types[/bold]
• [italic]bool[/italic] — truthy/falsy forms such as [bold]true[/bold]/[bold]false[/bold], [bold]1[/bold]/[bold]0[/bold], [bold]yes[/bold]/[bold]no[/bold] where documented as boolean.
• [italic]string[/italic] — free text, paths, model names, mode labels, etc.; the [italic]Description[/italic] column explains each variable.
• [italic]int[/italic] / [italic]float[/italic] — numeric parsing; a suffix like [bold](s)[/bold] means seconds. Ranges in the table (e.g. [bold]0.0–2.0[/bold], [bold]1–20[/bold]) are the usual bounds PKS enforces or documents.
• [italic]secret[/italic] — same storage as string; never commit real credentials.
• [italic]bool|int[/italic] — boolean or a positive integer, depending on the variable (see description).

The [italic]Values[/italic] column lists one of these labels plus an optional range. Model providers may still reject out-of-range temperatures or token limits even if PKS accepts the string."""
