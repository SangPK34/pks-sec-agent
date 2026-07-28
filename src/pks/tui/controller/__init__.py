"""
TUI Controller layer -- agent lifecycle and input routing.

Part of the MVC extraction from cai_terminal.py (4,500+ LOC).
"""

from pks.tui.controller.agent_controller import AgentController
from pks.tui.controller.input_controller import InputController, RouteKind, RouteDecision

__all__ = ["AgentController", "InputController", "RouteKind", "RouteDecision"]
