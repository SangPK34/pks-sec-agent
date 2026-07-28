"""
Module for PKS REPL prompt functionality.
"""

import shutil
import sys
import time
from functools import lru_cache
from prompt_toolkit import prompt, print_formatted_text  # pylint: disable=import-error
from prompt_toolkit.history import FileHistory  # pylint: disable=import-error
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory  # pylint: disable=import-error # noqa: E501
from prompt_toolkit.styles import Style  # pylint: disable=import-error
from prompt_toolkit.formatted_text import (  # pylint: disable=import-error
    FormattedText,
    to_formatted_text,
)
from pks.repl.commands import FuzzyCommandCompleter

# ── Brand color ──────────────────────────────────────────────────────────────
PKS_GREEN = "#58F9FF"

# Headless REPL input placeholder (grey italic when buffer empty; prompt_toolkit CLI only).
REPL_INPUT_PLACEHOLDER = "Type here, or ?"

_REPL_STDIN_EXHAUSTED_PENDING = False


def consume_repl_stdin_exhausted() -> bool:
    """True once after EOF on non-interactive stdin (pipe closed)."""
    global _REPL_STDIN_EXHAUSTED_PENDING
    out, _REPL_STDIN_EXHAUSTED_PENDING = _REPL_STDIN_EXHAUSTED_PENDING, False
    return out


# Cache for command shadow to avoid recalculating it too frequently
shadow_cache = {
    "text": "",
    "result": "",
    "last_update": 0,
    "update_interval": 0.1,  # Update at most every 100ms
}


@lru_cache(maxsize=32)
def get_command_shadow_cached(text):
    """Get command shadow suggestion with caching for repeated calls."""
    return FuzzyCommandCompleter().get_command_shadow(text)


def get_command_shadow(text):
    """Get command shadow suggestion with throttling."""
    current_time = time.time()

    # If the text hasn't changed, return the cached result
    if text == shadow_cache["text"]:
        return shadow_cache["result"]

    # If we've updated recently, return the cached result
    if (
        current_time - shadow_cache["last_update"] < shadow_cache["update_interval"]
        and shadow_cache["result"]
    ):
        return shadow_cache["result"]

    # Update the cache
    try:
        shadow = get_command_shadow_cached(text)
    except Exception:  # pylint: disable=broad-except
        # Guard against completer failures (e.g., optional deps missing)
        shadow = None

    if shadow and shadow.startswith(text):
        result = shadow[len(text) :]
    else:
        result = ""

    # Store in cache
    shadow_cache["text"] = text
    shadow_cache["result"] = result
    shadow_cache["last_update"] = current_time

    return result


def _terminal_width() -> int:
    """Get terminal width, with a sane default."""
    return shutil.get_terminal_size((80, 24)).columns


def _print_separator():
    """Print a horizontal separator line in PKS_GREEN."""
    pass


def create_prompt_style():
    """Create a style for the CLI."""
    return Style.from_dict(
        {
            "prompt": "bold #33d17a",
            "": "#7ee787",
            "placeholder": "#666666 italic",
            "bottom-separator": PKS_GREEN,
            "bottom-toolbar": "default noreverse",
            # PKS-themed completion popup: deep green background + white text,
            # with PKS green highlight for selected row.
            "completion-menu": "bg:#0f1b16 #e8efe9",
            "completion-menu.completion": "bg:#0f1b16 #e8efe9",
            "completion-menu.completion.current": "bg:#123526 #ff3355 bold",
            "scrollbar.background": "bg:#0f1b16",
            "scrollbar.button": "bg:#1f5a43",
            # Right-side submit hint: keys bold+italic, labels italic only
            "rprompt-hint": "#6b6b6b italic",
            "rprompt-hint-keys": "#6b6b6b bold italic",
        }
    )


def get_user_input(command_completer, key_bindings, history_file, toolbar_func, current_text):
    """
    Get user input with all prompt features.

    Args:
        command_completer: Command completer instance
        key_bindings: Key bindings instance
        history_file: Path to history file
        toolbar_func: Function to get toolbar content
        current_text: Reference to current text for command shadowing

    Returns:
        User input string
    """
    try:
        from pks.repl.ui.terminal_title import set_terminal_activity

        # idle: show the 💥 tab indicator while waiting for the operator's input (this also
        # applies the base title, so it must NOT be reset to a plain title here — that would
        # wipe the emoji every prompt).
        set_terminal_activity(False)
    except Exception:
        pass

    # Function to update current text, command shadow, and submit hint (right side)
    def get_rprompt():
        """Right prompt: optional command shadow + submit/newline hints."""
        shadow = get_command_shadow(current_text[0])
        # ↵ = Enter; Alt+↵ works on more terminals than Shift+↵ (see keybindings).
        hint_parts = []
        if shadow:
            return FormattedText(
                [
                    ("#888888", shadow),
                    ("class:rprompt-hint", " · "),
                    *hint_parts,
                ]
            )
        return FormattedText(hint_parts)

    # Print top separator line
    _print_separator()

    # After agent turns (compact Live, wait hints, streaming) the controlling TTY
    # can be left raw or with echo off; prompt_toolkit then treats Enter as LF only.
    try:
        from pks.util.streaming import restore_terminal_state

        restore_terminal_state(emit_trailing_newline=False)
    except Exception:
        pass

    # Close the CR→LF translation window. restore_terminal_state above runs
    # ``stty sane``, which re-enables ICRNL. Until prompt_toolkit installs its
    # own raw_mode, the kernel translates the CR from Enter into LF and queues
    # it; prompt_toolkit later reads that LF as ``c-j`` and triggers the
    # Shift+Enter binding (insert newline) instead of submitting. tcflush alone
    # only drains bytes queued so far — any keystroke landing in the window
    # between tcflush and prompt_toolkit's raw_mode setup falls into the same
    # trap. Clearing ICRNL/INLCR/IGNCR on the controlling TTY ensures Enter
    # delivers CR (``c-m``) regardless of how slowly the prompt comes up; then
    # tcflush drops any already-translated bytes from before this point.
    # Save the sane line-input state before temporarily disabling CR/LF
    # translations for prompt_toolkit. prompt_toolkit restores the state it
    # observed on entry, so without our own restore the following built-in
    # input() sees Enter as a literal CR (^M) instead of a completed line.
    _tty_fd = None
    _tty_attrs_before_prompt = None
    try:
        import termios as _ti_termios

        if sys.stdin.isatty():
            _tty_fd = sys.stdin.fileno()
            _tty_attrs_before_prompt = _ti_termios.tcgetattr(_tty_fd)
            _attrs = list(_tty_attrs_before_prompt)
            _attrs[0] &= ~(
                _ti_termios.ICRNL | _ti_termios.INLCR | _ti_termios.IGNCR
            )
            _ti_termios.tcsetattr(_tty_fd, _ti_termios.TCSANOW, _attrs)
            _ti_termios.tcflush(_tty_fd, _ti_termios.TCIFLUSH)
    except Exception:
        _tty_fd = None
        _tty_attrs_before_prompt = None

    # Wrap the original toolbar to prepend a green separator line
    def _toolbar_with_separator():
        original = toolbar_func() if toolbar_func else []
        if isinstance(original, list):
            return original
        if original:
            return list(to_formatted_text(original))
        return []

    # Get user input with all features
    try:
        result = prompt(
            [("class:prompt", "\n🤡 YOU > ")],
            placeholder=FormattedText([("class:placeholder", REPL_INPUT_PLACEHOLDER)]),
            completer=command_completer,
            style=create_prompt_style(),
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            key_bindings=key_bindings,
            bottom_toolbar=_toolbar_with_separator,
            complete_in_thread=True,
            complete_while_typing=True,  # Enable real-time completion
            enable_system_prompt=True,  # Enable shadow prediction
            mouse_support=False,  # Enable mouse support for menu navigation
            enable_suspend=True,  # Allow suspending with Ctrl+Z
            enable_open_in_editor=True,  # Allow editing with Ctrl+X Ctrl+E
            multiline=True,  # Enable multiline input
            rprompt=get_rprompt,
            color_depth=None,  # Auto-detect color support
        )
    except EOFError:
        global _REPL_STDIN_EXHAUSTED_PENDING
        try:
            if not sys.stdin.isatty():
                _REPL_STDIN_EXHAUSTED_PENDING = True
        except (AttributeError, OSError):
            _REPL_STDIN_EXHAUSTED_PENDING = True
        return ""
    finally:
        if _tty_fd is not None and _tty_attrs_before_prompt is not None:
            try:
                _ti_termios.tcsetattr(
                    _tty_fd,
                    _ti_termios.TCSANOW,
                    _tty_attrs_before_prompt,
                )
            except Exception:
                pass

    # Print bottom separator only when user submitted non-empty input,
    # so that empty Enter produces a single separator between prompts.
    if result and result.strip():
        _print_separator()

    print("\n")
    return result
