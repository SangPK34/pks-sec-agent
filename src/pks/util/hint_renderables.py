"""Shared Rich renderables for PKS CLI status lines (startup, model/tool waits, retries).

Badge: ``PKS`` / ``Ctrl+C`` on light grey pill, bold very dark text (no side accent blocks).
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from rich.text import Text

from pks.util.cli_palette import GREY_TEXT

if TYPE_CHECKING:
    from rich.console import RenderableType

# Light grey pill + bold near-black label (contrast on pale badge)
PKS_BADGE_BG = "#b8b8c4"
PKS_BADGE_FG = "#0a0a0c"

_PIPE_FRAMES = ("|", "/", "—", "\\")
# Same frames as ``rich.status.Status(..., spinner="dots")`` (startup / license check).
_BRAILLE_DOTS_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
_ACTIVITY_ICON_FRAMES = ("✶", "✸", "✹", "✺", "✹", "✷")
STARTUP_HINT_SPINNER_HZ = 12
ACTIVITY_BG = "#00363f"
ACTIVITY_FG = "#58F9FF"
ACTIVITY_HIGHLIGHT = "#e8feff"
ACTIVITY_DIM = "#37bfc7"


def terminal_columns() -> int:
    try:
        return max(40, shutil.get_terminal_size((80, 24)).columns)
    except Exception:
        return 80


def _pks_brand_badge() -> Text:
    return Text("PKS", style=f"bold {PKS_BADGE_FG} on {PKS_BADGE_BG}")


def pks_brand_badge_text() -> Text:
    """Public alias: grey pill ``PKS`` (same style as startup / model-tool wait hints)."""
    return _pks_brand_badge()


def build_pks_markup_line(markup: str) -> Text:
    """Grey PKS pill + Rich-markup body. Do not put ``[PKS]`` inside *markup*."""
    line = Text()
    line.append_text(_pks_brand_badge())
    line.append(" ")
    try:
        line.append(Text.from_markup(markup))
    except Exception:
        line.append(markup, style=GREY_TEXT)
    return line


def _ctrl_c_badge() -> Text:
    return Text("Ctrl+C", style=f"bold {PKS_BADGE_FG} on {PKS_BADGE_BG}")


def _truncate_body(s: str, max_len: int) -> str:
    s = s.replace("\n", " ").strip()
    if max_len <= 8 or len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"


def braille_dots_frame(tick: int) -> str:
    """One frame of the startup ``dots`` spinner (braille cycle)."""
    return _BRAILLE_DOTS_FRAMES[tick % len(_BRAILLE_DOTS_FRAMES)]


def _append_activity_badge(line: Text, action: str, frame_tick: int) -> None:
    """Append a purple activity badge with a moving three-character highlight."""
    line.append(" ", style=f"bold {ACTIVITY_DIM} on {ACTIVITY_BG}")
    sweep = frame_tick % (len(action) + 6) - 3
    for index, char in enumerate(action):
        distance = abs(index - sweep)
        if distance == 0:
            foreground = ACTIVITY_HIGHLIGHT
        elif distance <= 2:
            foreground = ACTIVITY_FG
        else:
            foreground = ACTIVITY_DIM
        line.append(char, style=f"bold {foreground} on {ACTIVITY_BG}")
    line.append(" ", style=f"bold {ACTIVITY_DIM} on {ACTIVITY_BG}")


def build_startup_hint_renderable(message: str) -> RenderableType:
    """Startup line: badge + static `` | `` + dim italic message (no interrupt suffix)."""
    msg = _truncate_body(message, max(20, terminal_columns() - 24))
    line = Text()
    line.append_text(_pks_brand_badge())
    line.append(" | ", style="dim")
    line.append(msg, style="italic dim")
    return line


def build_compact_live_wait_hint_row(body: str, *, frame_tick: int) -> Text:
    """Wait row inside the compact Live block with a locally animated activity badge.

    The compact ``Live`` owns the cursor, so both the star and badge shimmer are
    advanced manually instead of spawning a second Rich ``Status``.
    """
    msg = _truncate_body(body, max(20, terminal_columns() - 12))
    line = Text()
    line.append(
        _ACTIVITY_ICON_FRAMES[frame_tick % len(_ACTIVITY_ICON_FRAMES)],
        style=f"bold {ACTIVITY_FG}",
    )
    line.append(" ", style="")
    if "  Ctrl+C to interrupt  •  " in msg:
        action, suffix = msg.split("  Ctrl+C to interrupt  •  ", 1)
        _append_activity_badge(line, action, frame_tick)
        line.append("  Ctrl+C to interrupt  •  ", style="dim")
        line.append(suffix, style="dim")
        return line
    line.append_text(_pks_brand_badge())
    line.append(" | ", style="dim")
    line.append(msg, style="italic dim")
    return line


def build_model_wait_hint_renderable(
    body: str,
    *,
    frame_tick: int = 0,
    include_icon: bool = True,
) -> RenderableType:
    """Command Code-style model activity row with an animated badge sweep."""
    msg = _truncate_body(body, max(20, terminal_columns() - 8))
    line = Text()
    if "  Ctrl+C to interrupt  •  " in msg:
        action, suffix = msg.split("  Ctrl+C to interrupt  •  ", 1)
        if include_icon:
            line.append(
                _ACTIVITY_ICON_FRAMES[frame_tick % len(_ACTIVITY_ICON_FRAMES)],
                style=f"bold {ACTIVITY_FG}",
            )
            line.append(" ")
        _append_activity_badge(line, action, frame_tick)
        line.append("  Ctrl+C to interrupt  •  ", style="dim")
        line.append(suffix, style="dim")
    else:
        line.append(msg, style=f"bold {ACTIVITY_FG}")
    return line


def build_wait_hint_renderable(
    body: str,
    pipe_char: str,
    *,
    include_suffix: bool,
    reserve_for_suffix: int = 36,
) -> RenderableType:
    """Wait line: badge + rotating pipe + dim italic body; optional bold suffix + Ctrl+C badge."""
    cols = terminal_columns()
    budget = cols - 18 - (reserve_for_suffix if include_suffix else 0)
    body = _truncate_body(body, max(24, budget))
    line = Text()
    line.append_text(_pks_brand_badge())
    line.append(f" {pipe_char} ", style="dim")
    line.append(body, style="italic dim")
    if include_suffix:
        line.append("  —  ", style="bold")
        line.append_text(_ctrl_c_badge())
        line.append(" to interrupt", style="bold")
    return line


def pipe_frame(tick: int) -> str:
    return _PIPE_FRAMES[tick % 4]
