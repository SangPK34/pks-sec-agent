"""Canonical `/settings` subcommands for REPL help and unknown-subcommand text."""

from __future__ import annotations

from pks.repl.ui.banner import _PKS_GREEN

# (name, one-line description) — single source for `/h settings` and unknown-subcommand list
SETTINGS_CLI_SUBCOMMANDS: tuple[tuple[str, str], ...] = (
    ("faq", "FAQ and troubleshooting"),
    ("validate", "Validate API keys"),
    ("status", "System status"),
    ("language", "Interface language"),
    ("ollama", "Ollama setup guide"),
)


def settings_help_panel_subcommand_bullets() -> str:
    """Rich markup: one bullet per canonical subcommand (no trailing newline)."""
    return "\n".join(
        f"• [bold {_PKS_GREEN}]/settings {name}[/bold {_PKS_GREEN}] - {desc}"
        for name, desc in SETTINGS_CLI_SUBCOMMANDS
    )
