"""
PKS Cut The Rope (CTR) Module

This package provides the Cut The Rope security game solver for strategic analysis.

Heavy dependencies (numpy, scipy, networkx, …) are loaded only when you access the
corresponding attributes or submodules. This allows ``from pks.ctr.paths import …``
and the TUI to start without installing the optional ``[data]`` / ``[viz]`` extras.
"""

from __future__ import annotations

import importlib
from typing import Any, Dict, Tuple

# (module_path, attribute_name)
_LAZY_ATTRS: Dict[str, Tuple[str, str]] = {
    "find_and_add_entry_node": ("pks.ctr.core", "find_and_add_entry_node"),
    "generate_game_elements": ("pks.ctr.core", "generate_game_elements"),
    "merge_targets_with_multi_edges": ("pks.ctr.core", "merge_targets_with_multi_edges"),
    "core_set_default_weight": ("pks.ctr.core", "core_set_default_weight"),
    "core_set_debug_mode": ("pks.ctr.core", "core_set_debug_mode"),
    "ctr_core_main": ("pks.ctr.core", "main"),
    "clean_subgraph": ("pks.ctr.create_subgraphs", "clean_subgraph"),
    "create_defender_subgraph": ("pks.ctr.create_subgraphs", "create_defender_subgraph"),
    "generate_defender_subgraphs": ("pks.ctr.create_subgraphs", "generate_defender_subgraphs"),
    "visualize_subgraphs": ("pks.ctr.create_subgraphs", "visualize_subgraphs"),
    "create_graph_from_agent_output": ("pks.ctr.attack_graph", "create_graph_from_agent_output"),
    "plot_attack_graph": ("pks.ctr.attack_graph", "plot_attack_graph"),
    "create_cleaned_graph_for_visualization": (
        "pks.ctr.attack_graph",
        "create_cleaned_graph_for_visualization",
    ),
    "compute_edge_probabilities_offline": (
        "pks.ctr.probability_computation",
        "compute_edge_probabilities_offline",
    ),
    "get_log_tokens": ("pks.ctr.probability_computation", "get_log_tokens"),
    "visualize_baseline_results": ("pks.ctr.visualization", "visualize_baseline_results"),
}

__all__ = list(_LAZY_ATTRS.keys())


def __getattr__(name: str) -> Any:
    if name in _LAZY_ATTRS:
        mod_path, attr = _LAZY_ATTRS[name]
        mod = importlib.import_module(mod_path)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
