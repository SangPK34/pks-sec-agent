"""Ensure packaged prompt markdown loads through `load_prompt_template` (Mako render succeeds)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pks.util import load_prompt_template
from pks.util.prompts import _MICRO_PROFILE_PATHS

_PROMPT_DIR = Path(__file__).resolve().parents[2] / "src" / "pks" / "prompts"
_SYSTEM_PROMPT_RELPATHS = tuple(
    f"prompts/{path.name}" for path in sorted(_PROMPT_DIR.glob("*.md"))
)


def test_system_templates_load(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PKS_CYBER_PROFILE", raising=False)
    for rel in _SYSTEM_PROMPT_RELPATHS:
        text = load_prompt_template(rel)
        assert isinstance(text, str)
        assert len(text) > 80, f"prompt unexpectedly short: {rel}"


def test_micro_profile_templates_load(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PKS_CYBER_PROFILE", raising=False)
    for rel in sorted(set(_MICRO_PROFILE_PATHS.values())):
        text = load_prompt_template(rel)
        assert isinstance(text, str)
        assert len(text) > 40, f"micro prompt unexpectedly short: {rel}"
        assert "MICRO-PROFILE" in text.upper(), rel


def test_prompt_examples_match_current_tool_contract() -> None:
    stale_two_positional_args = re.compile(
        r'generic_linux_command\("[^"]+",\s*"'
    )
    violations: list[str] = []
    for path in sorted(_PROMPT_DIR.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        if stale_two_positional_args.search(text):
            violations.append(str(path.relative_to(_PROMPT_DIR)))

    assert violations == []


def test_prompt_contracts_have_no_stale_machine_or_rule_references() -> None:
    forbidden = (
        "Override Rule ",
        "/home/sangpk05",
        "CANNOT see images",
        "authoritative for this turn",
    )
    violations: list[str] = []
    for path in sorted(_PROMPT_DIR.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for phrase in forbidden:
            if phrase in text:
                violations.append(f"{path.relative_to(_PROMPT_DIR)}: {phrase}")

    assert violations == []
