"""
Shared CLI headless colour constants (Layout 1 — brand palette).

Single source for terminal.py, streaming.py, sudo, sensitive guard, questionary.
Do not introduce cyan in this family.
"""

from __future__ import annotations

# Brand
PKS_GREEN = "#58F9FF"
FINAL_PANEL_BG = "default"
PKS_BORDER = "#979797"

# Text / chrome
GREY_TEXT = "#9a9a9a"
GREY_HINT = "#7a7a8a"
PIPE_GREY = "#888888"

# Wizard / continuous-ops headings (warm brown, stays within green-grey brand lane)
WIZARD_BROWN = "#b89f6a"

# Same accent as the ``repl.ui.banner`` YOLO promo line (amber on most terminals)
BANNER_PROMO_YELLOW = "bold yellow"

# Pills
BADGE_TIME_BG = "#c4c4c4"
BADGE_TIME_FG = "#1a1a1a"
BADGE_ENV_BG = "#2D4F56"
BADGE_ENV_FG = "white"

# Accents (Rich built-ins where hex is awkward)
YELLOW_WARN = "bold yellow"
# Warmer warning line (matches e.g. settings Monolith ``orange1`` accents)
ORANGE_WARN = "bold orange1"
YELLOW_ON = "bold black on bright_yellow"
ERROR_PILL = "bold white on bright_red"
COMPLETED_PILL = "bold black on #33d17a"
