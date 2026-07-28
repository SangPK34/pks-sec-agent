"""
TUI View layer -- layout composition and CSS extracted from pks_terminal.py.

Part of the MVC extraction from the original 4,500+ LOC monolith.
"""

from pks.tui.view.main_view import (
    PKS_TERMINAL_CSS,
    compose_main_layout,
    register_pks_themes,
    get_help_basic_content,
    get_help_advanced_content,
    get_help_protips_content,
    update_tab_appearance,
)

__all__ = [
    "PKS_TERMINAL_CSS",
    "compose_main_layout",
    "register_pks_themes",
    "get_help_basic_content",
    "get_help_advanced_content",
    "get_help_protips_content",
    "update_tab_appearance",
]
