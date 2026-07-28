"""REPL command for selecting an OpenAI-compatible model name."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from rich import box
from rich.console import Console
from rich.table import Table

from pks.model_catalog import MODELS, find_model, models_by_provider
from pks.repl.commands.base import Command, register_command
from pks.repl.ui.banner import _PKS_GREEN

console = Console()

_MODEL_CATEGORIES = models_by_provider()
_REASONING_LEVELS = {"low", "medium", "high", "xhigh", "max"}


def get_predefined_model_categories() -> Dict[str, List[Dict[str, str]]]:
    return {
        category: [
            {
                "name": model.model_id,
                "description": f"{model.name} · {model.context} · {model.best_for}",
            }
            for model in models
        ]
        for category, models in _MODEL_CATEGORIES.items()
    }


def get_all_predefined_models() -> List[Dict[str, Any]]:
    result = []
    for category, models in _MODEL_CATEGORIES.items():
        for model in models:
            result.append(
                {
                    "name": model.model_id,
                    "provider": category,
                    "category": category,
                    "description": f"{model.name} · {model.context} · {model.best_for}",
                }
            )
    return result


def get_predefined_model_names() -> List[str]:
    return [model.model_id for model in MODELS]


def load_all_available_models() -> tuple[List[str], List[Dict[str, Any]]]:
    """Return the local catalog; custom endpoint names remain selectable by text."""
    return get_predefined_model_names(), []


def _model_table(title: str) -> Table:
    table = Table(
        title=title,
        box=box.ROUNDED,
        border_style=_PKS_GREEN,
        header_style=f"bold {_PKS_GREEN}",
    )
    table.add_column("#", justify="right")
    table.add_column("Model", style=_PKS_GREEN)
    table.add_column("Provider")
    table.add_column("Context")
    return table


def _print_catalog(search_term: str | None = None, limit: int | None = None) -> None:
    matches = [
        model
        for model in MODELS
        if not search_term
        or search_term
        in f"{model.model_id} {model.name} {model.provider}".lower()
    ]
    visible = matches[:limit] if limit else matches
    table = _model_table(
        f"Frontier models ({len(matches)}/{len(MODELS)})"
    )
    for model in visible:
        table.add_row(
            str(MODELS.index(model) + 1),
            model.model_id,
            model.provider,
            model.context,
        )
    console.print(table)
    if limit and len(matches) > limit:
        console.print(
            f"[dim]Showing top {limit}. Use [bold {_PKS_GREEN}]/model show[/bold "
            f"{_PKS_GREEN}] for all {len(MODELS)}, or "
            f"[bold {_PKS_GREEN}]/model show <provider/name>[/bold {_PKS_GREEN}].[/dim]"
        )
    console.print(
        f"[dim]Catalog IDs are defaults, not a provider guarantee. Any exact model ID "
        f"served by OPENAI_BASE_URL can be selected directly: "
        f"[bold {_PKS_GREEN}]/model <name>[/bold {_PKS_GREEN}].[/dim]"
    )


class ModelCommand(Command):
    def __init__(self):
        super().__init__(
            name="/model",
            description="View or change the current LLM model",
            aliases=["/mod"],
        )
        self.cached_models = get_predefined_model_names()
        self.cached_model_numbers = {
            str(index): name for index, name in enumerate(self.cached_models, 1)
        }

    def handle(self, args: Optional[List[str]] = None) -> bool:
        values = list(args or [])
        if not values:
            console.print(
                f"Current model: [bold {_PKS_GREEN}]"
                f"{os.getenv('PKS_MODEL', 'gpt-5.6-terra')}[/bold {_PKS_GREEN}]"
            )
            effort = os.getenv("PKS_REASONING_EFFORT", "").strip() or "off"
            console.print(f"Reasoning effort: [bold]{effort}[/bold]")
            _print_catalog(limit=20)
            return True

        if values[0] == "show":
            search = " ".join(values[1:]).lower() or None
            _print_catalog(search)
            return True
        if values[0] in {"reasoning", "thinking"}:
            return self._handle_reasoning(values[1:])
        return self.handle_model_command(values)

    def _handle_reasoning(self, args: List[str]) -> bool:
        if not args:
            current = os.getenv("PKS_REASONING_EFFORT", "").strip() or "off"
            console.print(f"Reasoning effort: [bold {_PKS_GREEN}]{current}[/bold {_PKS_GREEN}]")
            return True

        value = args[0].strip().lower()
        if value in {"off", "none", "false", "0"}:
            os.environ.pop("PKS_REASONING_EFFORT", None)
            console.print("Reasoning effort disabled.")
            return True
        if value not in _REASONING_LEVELS:
            console.print(
                "[red]Use off, low, medium, high, xhigh, or max.[/red]"
            )
            return True
        current_model = os.getenv("PKS_MODEL", "gpt-5.6-terra")
        catalog_model = find_model(current_model)
        if catalog_model and value not in catalog_model.efforts:
            supported = ", ".join(catalog_model.efforts) or "none"
            console.print(
                f"[red]{catalog_model.name} supports effort: {supported}.[/red]"
            )
            return True
        os.environ["PKS_REASONING_EFFORT"] = value
        console.print(
            f"Reasoning effort changed to [bold {_PKS_GREEN}]{value}[/bold {_PKS_GREEN}]."
        )
        return True

    def handle_model_command(self, args: List[str]) -> bool:
        if not args or not args[0].strip():
            console.print("[red]Missing model name or number.[/red]")
            return True

        requested = args[0].strip()
        if requested.isdigit():
            model_name = self.cached_model_numbers.get(requested)
            if model_name is None:
                console.print("[red]Model number is out of range.[/red]")
                return True
        else:
            model_name = requested

        os.environ["PKS_MODEL"] = model_name
        selected = find_model(model_name)
        effort = os.getenv("PKS_REASONING_EFFORT", "").strip().lower()
        if selected and effort and effort not in selected.efforts:
            os.environ.pop("PKS_REASONING_EFFORT", None)
            console.print(
                f"[dim]Reasoning effort cleared; {selected.name} does not support "
                f"{effort}.[/dim]"
            )
        console.print(
            f"Model changed to [bold {_PKS_GREEN}]{model_name}[/bold {_PKS_GREEN}]. "
            "[dim]Applied on the next interaction.[/dim]"
        )
        return True


_MODEL_COMMAND = ModelCommand()
register_command(_MODEL_COMMAND)


class EffortCommand(Command):
    def __init__(self):
        super().__init__(
            name="/effort",
            description="View or change reasoning effort for the current model",
            aliases=["/thinking"],
        )

    def handle(self, args: Optional[List[str]] = None) -> bool:
        return _MODEL_COMMAND._handle_reasoning(list(args or []))


register_command(EffortCommand())
