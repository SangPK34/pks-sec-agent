"""Deprecated REPL commands ``/config``, ``/cfg`` — deprecation notice only."""

from __future__ import annotations

from typing import Optional

from rich.console import Console  # pylint: disable=import-error
from rich.panel import Panel  # pylint: disable=import-error

from pks.repl.commands.base import Command, register_command
from pks.repl.ui.banner import _PKS_GREEN, _quick_guide_subpanel_title

console = Console()


def print_config_deprecated_message(out: Optional[Console] = None) -> None:
    """Single panel redirecting users to ``/env`` (also used by ``/help config``).

    ``out`` defaults to this module's console so ``/config`` and tests that patch
    ``help.console`` can route output consistently.
    """
    target = out if out is not None else console
    body = (
        "[bold]/config[/bold] is deprecated. Use [bold #ff3355]/env[/bold #ff3355] instead:\n\n"
        "• [bold #ff3355]/env[/bold #ff3355] — [dim]PKS_[/dim] / [dim]CTF_[/dim] keys in this process\n"
        "• [bold #ff3355]/env list[/bold #ff3355] — full catalog\n"
        "• [bold #ff3355]/env get <n|NAME>[/bold #ff3355] / "
        "[bold #ff3355]/env set <n|NAME> <value...>[/bold #ff3355]\n"
        "• [bold #ff3355]/env default[/bold #ff3355] — restore all catalog defaults"
    )
    target.print(
        Panel(
            body,
            title=_quick_guide_subpanel_title("Deprecated command"),
            title_align="left",
            padding=(1, 1),
            border_style=_PKS_GREEN,
        )
    )


class ConfigCommand(Command):
    """Stub: print deprecation only."""

    def __init__(self):
        super().__init__(
            name="/config",
            description="Deprecated: use /env for environment variables",
            aliases=["/cfg"],
        )

    def handle(self, args=None):  # pylint: disable=unused-argument
        print_config_deprecated_message()
        return True


register_command(ConfigCommand())
