"""CLI entry-point for PKS (Cybersecurity AI Framework).

This module is a thin orchestrator:
  1. Bootstraps the environment via ``cli_setup``
  2. Parses CLI arguments (argparse)
  3. Dispatches to TUI mode or headless REPL (``cli_headless.run_pks_cli``)

Heavy logic lives in:
  - ``pks.cli_setup``    -- .env loading, warning/logging config, CTF init
  - ``pks.cli_headless`` -- interactive REPL loop, agent execution, parallel mode
"""

# --- Bootstrap MUST happen before any other pks imports ---
from pks.cli_setup import bootstrap as _bootstrap
_bootstrap()

# --- Suppress "Event loop is closed" noise on exit (Python 3.12+) ----------
# BaseSubprocessTransport.__del__ tries to close pipes via a closed loop.
# This is harmless but prints ugly tracebacks. Patch it early.
import asyncio.base_subprocess as _abs
_original_bst_del = _abs.BaseSubprocessTransport.__del__

def _quiet_bst_del(self):
    try:
        _original_bst_del(self)
    except RuntimeError:
        pass  # "Event loop is closed" during interpreter shutdown — ignore

_abs.BaseSubprocessTransport.__del__ = _quiet_bst_del
# ---------------------------------------------------------------------------

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Optional

from rich.console import Console

from pks.config import get_config
from pks.cli_setup import create_last_log_symlink
import pks.cli_setup as _cli_setup  # for ctf_global backward compat
from pks.repl.commands.parallel import (
    PARALLEL_CONFIGS,
    load_parallel_config_from_yaml,
)
from pks.sdk.agents import set_tracing_disabled
from wasabi import color
from pks.util import ensure_litellm_transcription_support
from pks.repl.ui.banner import display_banner
from pks.repl.ui.startup_hints import StartupHints

# Re-export for backward compatibility (other modules import from pks.cli)
__all__ = [
    "main",
    "run_pks_cli",
    "update_agent_models_recursively",
    "create_last_log_symlink",
    "START_TIME",
    "ctf_global",
]


def _resolve_model_name(model_name: str | None) -> str:
    """Return the configured model name."""
    return (model_name or os.getenv("PKS_MODEL") or "gpt-5.6-terra").strip()


def __getattr__(name):
    """Lazy re-export: headless CLI (heavy import) and cli_setup globals."""
    if name in ("run_pks_cli", "update_agent_models_recursively", "START_TIME"):
        import pks.cli_headless as _headless

        globals()["run_pks_cli"] = _headless.run_pks_cli
        globals()["update_agent_models_recursively"] = _headless.update_agent_models_recursively
        globals()["START_TIME"] = _headless.START_TIME
        return globals()[name]
    if name in ("ctf_global", "messages_ctf", "ctf_init", "first_ctf_time", "previous_ctf_name"):
        return getattr(_cli_setup, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _ensure_headless_bound() -> None:
    """Import cli_headless into this module's globals.

    ``__getattr__`` only runs for ``import pks.cli; pks.cli.run_pks_cli`` style
    access; ``LOAD_GLOBAL`` inside this file does not trigger it, so internal
    callers need an explicit bind before using ``run_pks_cli`` /
    ``update_agent_models_recursively``.
    """
    g = globals()
    if "run_pks_cli" in g:
        return
    import pks.cli_headless as _headless

    g["run_pks_cli"] = _headless.run_pks_cli
    g["update_agent_models_recursively"] = _headless.update_agent_models_recursively
    g["START_TIME"] = _headless.START_TIME


def main():
    """Parse CLI arguments and dispatch to the appropriate mode."""
    # First feedback ASAP (Rich only — avoids importing cli_headless until headless REPL).
    boot_console = Console()
    boot = StartupHints(boot_console)
    boot.start("Starting PKS framework...")

    # Fresh shared cross-agent blackboard for this session.
    try:
        from pks.util import blackboard as _pks_bb
        _pks_bb.reset()
    except Exception:
        pass

    # --- System dependency check ---
    try:
        from pks.util_ext import check_system_dependencies, display_missing_dependencies_error
        all_ok, missing = check_system_dependencies()
        if not all_ok:
            boot.stop()
            display_missing_dependencies_error(missing)
            sys.exit(1)
    except Exception:
        pass

    # --- Argparse ---
    parser = argparse.ArgumentParser(
        prog="pks",
        description="Cybersecurity AI Framework",
        add_help=True,
        allow_abbrev=False,
    )
    parser.add_argument("--tui", action="store_true", help="Launch PKS in Textual UI mode")
    parser.add_argument("--yaml", dest="yaml_path", metavar="FILE", help="Load agent definitions from YAML")
    parser.add_argument("--prompt", dest="prompt_override", metavar="TEXT", help="Initial prompt to execute immediately")
    parser.add_argument("--version", action="store_true", help="Show PKS version and exit")
    parser.add_argument("--update", action="store_true", help="Check for updates and install if available")
    parser.add_argument("--continue", "-c", action="store_true", dest="continue_mode", help="Enable continuous mode")
    parser.add_argument(
        "--yolo",
        action="store_true",
        help="YOLO mode: skip sensitive-command confirmation (auto-approve tool shell runs; unsafe)",
    )
    parser.add_argument("--api", action="store_true", help="Launch as HTTP API backend")
    cfg = get_config()
    if os.getenv("PKS_AGENT_TYPE", "").strip() == "selection_agent":
        os.environ["PKS_AGENT_TYPE"] = "root_agent"
    parser.add_argument("--api-host", default=cfg.api_host)
    parser.add_argument("--api-port", type=int, default=cfg.api_port)
    parser.add_argument("--api-reload", action="store_true", default=cfg.api_reload)
    parser.add_argument("--api-workers", type=int, default=cfg.api_workers)
    try:
        parsed_args, remaining_args = parser.parse_known_args()
    except SystemExit:
        boot.stop()
        raise

    _exit_if_removed_resume_cli_flags(sys.argv[1:])

    # --- --yolo (must run before agent/tools: disables sensitive-command prompts) ---
    if parsed_args.yolo:
        os.environ["PKS_YOLO"] = "true"

    # --- --version ---
    if parsed_args.version:
        boot.stop()
        try:
            import importlib.metadata
            print(f"PKS Framework v{importlib.metadata.version('pks-framework')}")
        except Exception:
            print("PKS Framework (development version)")
        sys.exit(0)

    # --- --update ---
    if parsed_args.update:
        boot.stop()
        _handle_update_command()
        return

    # --- YAML loading ---
    resolved_yaml_path: Optional[Path] = None
    if parsed_args.yaml_path:
        boot.update("Loading parallel agent configuration...")
        candidate_path = Path(parsed_args.yaml_path).expanduser()
        quiet_load = parsed_args.tui
        if not load_parallel_config_from_yaml(candidate_path, quiet=quiet_load):
            boot.stop()
            if quiet_load:
                print(f"Error: failed to load agents config '{parsed_args.yaml_path}'", file=sys.stderr)
            sys.exit(2)
        resolved_yaml_path = candidate_path.resolve()

        if not parsed_args.tui:
            boot.stop()
            print(f"Loaded {len(PARALLEL_CONFIGS)} parallel agents from {resolved_yaml_path}", file=sys.stderr)
            _maybe_enable_auto_run(resolved_yaml_path)
            boot.start("Continuing startup...", leading_blank=False)

    # --- API server mode ---
    if parsed_args.api:
        boot.stop()
        from pks.api.server import run_api_server
        try:
            run_api_server(
                host=parsed_args.api_host,
                port=parsed_args.api_port,
                reload=parsed_args.api_reload,
                workers=parsed_args.api_workers,
            )
        except KeyboardInterrupt:
            sys.exit(0)
        return

    # --- TUI mode ---
    if parsed_args.tui:
        boot.stop()
        if resolved_yaml_path:
            os.environ["PKS_TUI_STARTUP_YAML"] = str(resolved_yaml_path)
        shared_prompt = parsed_args.prompt_override
        if not shared_prompt and remaining_args:
            shared_prompt = " ".join(remaining_args).strip()
        if shared_prompt:
            os.environ["PKS_TUI_SHARED_PROMPT"] = shared_prompt
        os.environ["PKS_TUI_MODE"] = "true"

        from pks.tui.display.context_preservation import enable_task_context_propagation
        enable_task_context_propagation()
        from pks.tui.pks_terminal import run_pks_tui
        run_pks_tui()
        return

    # --- Config validation at startup [B] ---
    config_warnings = cfg.validate()
    if config_warnings:
        boot.stop()
        console = Console(stderr=True)
        for w in config_warnings:
            console.print(f"[yellow]⚠ Config warning: {w}[/yellow]")

    # --- Headless CLI mode ---
    boot.set_message("Initializing CLI output...")
    # Wire OutputManager for CLI output events [P+T].
    # Compact mode (q3=b) is the default; opting out via PKS_COMPACT_REPL=0
    # falls back to the legacy verbose CLIOutputHandler.
    from pks.repl.ui.compact_wiring import install_compact_ui, is_compact_enabled
    if is_compact_enabled():
        install_compact_ui()
    else:
        from pks.output import OUTPUT, CLIOutputHandler
        OUTPUT.subscribe(CLIOutputHandler())

    from pks.util import ensure_litellm_logging_worker_loop_safety
    patch_applied = ensure_litellm_transcription_support()
    ensure_litellm_logging_worker_loop_safety()
    if not patch_applied:
        boot.stop()
        print(color("LiteLLM transcription support could not be enabled", color="red"))
        boot.start("Continuing startup...", leading_blank=False)

    boot.stop()
    try:
        from pks.repl.ui.terminal_title import set_terminal_window_title

        set_terminal_window_title()
    except Exception:
        pass
    display_banner(boot_console, model=cfg.model, agent_type=cfg.agent_type)
    boot_console.print()
    boot.start("Loading agent and session runtime...", leading_blank=False)

    initial_prompt = _resolve_initial_prompt(parsed_args, remaining_args)
    boot.update("Resolving agent from configuration...")
    _ensure_headless_bound()
    agent = _resolve_agent()
    _agent_type_resolved = os.getenv("PKS_AGENT_TYPE", cfg.agent_type)
    os.environ.setdefault(
        "PKS_AGENT_ROUTE_MODE",
        "auto"
        if _agent_type_resolved in ("root_agent", "selection_agent", "orchestration_agent")
        else "pinned",
    )
    boot.stop()
    run_pks_cli(
        agent,
        initial_prompt=initial_prompt,
        continue_mode=getattr(parsed_args, "continue_mode", False),
        console=boot_console,
        skip_startup_banner=True,
    )


# ---------------------------------------------------------------------------
# Private helpers for main()
# ---------------------------------------------------------------------------

def _handle_update_command():
    from pks.util_ext import (
        check_for_updates,
        perform_update,
        prompt_for_update,
        user_env_requests_auto_framework_update,
    )

    console = Console()
    console.print("[dim white]Checking for updates…[/dim white]")
    update_info = check_for_updates()
    if update_info and update_info.get("update_available"):
        if user_env_requests_auto_framework_update() or prompt_for_update(update_info):
            sys.exit(0 if perform_update() else 1)
        else:
            console.print("[italic dim white]Update cancelled.[/italic dim white]")
    elif update_info is not None:
        console.print(
            f"[bold {PKS_GREEN}]✓[/bold {PKS_GREEN}] "
            f"[bold white]pks-framework {update_info.get('current_version', '')} "
            f"is up to date.[/bold white]"
        )
    else:
        console.print(
            "[yellow]Could not check for updates[/yellow] "
            "[dim white](network error or index unreachable).[/dim white]"
        )
        sys.exit(1)
    sys.exit(0)


def _maybe_enable_auto_run(resolved_yaml_path):
    from pks.config_loader import load_agents_config, extract_agent_definitions
    try:
        data, _ = load_agents_config(resolved_yaml_path)
        agents, metadata, _ = extract_agent_definitions(data)
        has_auto_run = any(a.get('auto_run', metadata.get('auto_run', False)) for a in agents)
        if has_auto_run and PARALLEL_CONFIGS:
            os.environ["PKS_AUTO_RUN_PARALLEL"] = "1"
            print("Auto-run enabled for parallel agents. They will execute automatically.", file=sys.stderr)
    except Exception:
        pass


def _resolve_initial_prompt(parsed_args, remaining_args):
    source = parsed_args.prompt_override or (" ".join(remaining_args) if remaining_args else None)
    if not source:
        return None

    initial_prompt = source
    if ';' in initial_prompt:
        commands = [cmd.strip() for cmd in initial_prompt.split(';')]
        if len(commands) > 1:
            initial_prompt = commands[0]
            from pks.repl.commands.queue import add_to_queue
            for cmd in commands[1:]:
                if cmd:
                    add_to_queue(cmd)
            os.environ["PKS_AUTO_RUN_QUEUE"] = "1"
    return initial_prompt


def _resolve_agent():
    cfg = get_config()
    agent_type = cfg.agent_type

    from pks.agents.patterns import get_pattern
    pattern = get_pattern(agent_type)

    if pattern and hasattr(pattern, "configs"):
        console = Console()
        console.print(f"[cyan]Loading pattern from PKS_AGENT_TYPE: {agent_type}[/cyan]")
        PARALLEL_CONFIGS.clear()
        for idx, config in enumerate(pattern.configs, 1):
            config.id = f"P{idx}"
            PARALLEL_CONFIGS.append(config)
        if len(PARALLEL_CONFIGS) >= 2:
            os.environ["PKS_PARALLEL"] = str(len(PARALLEL_CONFIGS))
            os.environ["PKS_PARALLEL_AGENTS"] = ",".join(c.agent_name for c in PARALLEL_CONFIGS)
        console.print(f"[green]Loaded parallel pattern: {pattern.description}[/green]")
        for idx, config in enumerate(PARALLEL_CONFIGS, 1):
            resolved_model = _resolve_model_name(config.model)
            model_info = f" [{resolved_model}]"
            console.print(f"  [P{idx}] {config.agent_name}{model_info}")
        from pks.agents import get_agent_by_name
        agent = get_agent_by_name(PARALLEL_CONFIGS[0].agent_name, agent_id="P1")
    else:
        from pks.agents import get_agent_by_name
        from pks.sdk.agents.simple_agent_manager import DEFAULT_SESSION_AGENT_ID

        agent = get_agent_by_name(agent_type, agent_id=DEFAULT_SESSION_AGENT_ID)

    from pks.sdk.agents.simple_agent_manager import AGENT_MANAGER
    AGENT_MANAGER.switch_to_single_agent(agent, getattr(agent, "name", agent_type))

    if hasattr(agent, "model"):
        if hasattr(agent.model, "disable_rich_streaming"):
            agent.model.disable_rich_streaming = True
        if hasattr(agent.model, "suppress_final_output"):
            agent.model.suppress_final_output = False

    update_agent_models_recursively(agent, cfg.model)
    return agent


def _exit_if_removed_resume_cli_flags(argv: list[str]) -> None:
    """Inform users that --resume / --logpath were removed (use REPL /resume)."""
    removed: set[str] = set()
    for arg in argv:
        if arg == "--resume" or arg.startswith("--resume="):
            removed.add("--resume")
        elif arg == "--logpath" or arg.startswith("--logpath="):
            removed.add("--logpath")
    if not removed:
        return
    console = Console(stderr=True)
    flags = ", ".join(sorted(removed))
    console.print(
        f"[bold #ff3355]Removed CLI flags:[/bold #ff3355] {flags}.\n"
        "[dim]Start PKS, then use [/dim][bold #ff3355]/resume[/bold #ff3355][dim] "
        "(pick from the same recent list as [/dim][bold #ff3355]/sessions[/bold #ff3355][dim]), "
        "[/dim][bold #ff3355]/resume last[/bold #ff3355][dim], a `.jsonl` path, a directory, "
        "or [/dim][bold #ff3355]/sessions <n>[/bold #ff3355][dim] for a longer list.[/dim]"
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
