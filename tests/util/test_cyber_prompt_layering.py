"""Tests for `_compose_cyber_layered_prompt` and micro-profile registry.

No template bundle I/O beyond compose.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from pks.util.prompts import (
    _MICRO_PROFILE_PATHS,
    _compose_cyber_layered_prompt,
    _load_micro_profile_text,
    _upsert_compacted_memory_block,
    create_system_prompt_renderer,
    load_prompt_template,
)


def test_compose_cyber_layering_disabled_returns_base_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PKS_CYBER_PROFILE", "false")
    try:
        out = _compose_cyber_layered_prompt(
            "BASE_ONLY_MARKER",
            None,
            cyber_micro_profile_key="redteam",
        )
        assert out == "BASE_ONLY_MARKER"
    finally:
        monkeypatch.delenv("PKS_CYBER_PROFILE", raising=False)


def test_compose_full_includes_baseline_and_micro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PKS_CYBER_PROFILE", "true")
    monkeypatch.setenv("PKS_CYBER_PROFILE_MODE", "full")
    try:
        out = _compose_cyber_layered_prompt(
            "TAIL_BASE_MARKER",
            None,
            cyber_micro_profile_key="selection",
        )
        assert "PKS CYBER BASELINE" in out
        assert "AGENT MICRO-PROFILE: ROOT" in out.upper()
        assert "TAIL_BASE_MARKER" in out
    finally:
        monkeypatch.delenv("PKS_CYBER_PROFILE", raising=False)
        monkeypatch.delenv("PKS_CYBER_PROFILE_MODE", raising=False)


def test_compose_lite_uses_lite_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PKS_CYBER_PROFILE", "true")
    monkeypatch.setenv("PKS_CYBER_PROFILE_MODE", "lite")
    try:
        out = _compose_cyber_layered_prompt(
            "X",
            None,
            cyber_micro_profile_key="ctf",
        )
        assert "PKS CYBER BASELINE (LITE)" in out
        assert "AGENT MICRO-PROFILE: CTF" in out.upper()
    finally:
        monkeypatch.delenv("PKS_CYBER_PROFILE", raising=False)
        monkeypatch.delenv("PKS_CYBER_PROFILE_MODE", raising=False)


def test_compose_mode_off_env_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PKS_CYBER_PROFILE", "true")
    monkeypatch.setenv("PKS_CYBER_PROFILE_MODE", "off")
    try:
        out = _compose_cyber_layered_prompt(
            "PLAIN",
            None,
            cyber_micro_profile_key="web",
        )
        assert out == "PLAIN"
    finally:
        monkeypatch.delenv("PKS_CYBER_PROFILE", raising=False)
        monkeypatch.delenv("PKS_CYBER_PROFILE_MODE", raising=False)


@pytest.mark.parametrize(
    "key",
    ("redteam", "blueteam", "guardrail", "compliance"),
)
def test_compose_representative_micro_keys(
    key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PKS_CYBER_PROFILE", "true")
    monkeypatch.setenv("PKS_CYBER_PROFILE_MODE", "full")
    try:
        out = _compose_cyber_layered_prompt(
            f"MARKER_{key}",
            None,
            cyber_micro_profile_key=key,
        )
        assert f"MARKER_{key}" in out
        assert "PKS CYBER BASELINE" in out
        assert "MICRO-PROFILE" in out.upper()
    finally:
        monkeypatch.delenv("PKS_CYBER_PROFILE", raising=False)
        monkeypatch.delenv("PKS_CYBER_PROFILE_MODE", raising=False)


def test_every_micro_profile_registry_key_composes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each `_MICRO_PROFILE_PATHS` entry must load and layer with the full baseline."""
    monkeypatch.setenv("PKS_CYBER_PROFILE", "true")
    monkeypatch.setenv("PKS_CYBER_PROFILE_MODE", "full")
    try:
        for profile_key in sorted(_MICRO_PROFILE_PATHS):
            text = _load_micro_profile_text(profile_key)
            assert text.strip(), f"empty micro profile: {profile_key}"
            composed = _compose_cyber_layered_prompt(
                "END_MARKER",
                None,
                cyber_micro_profile_key=profile_key,
            )
            assert "END_MARKER" in composed
            assert "PKS CYBER BASELINE" in composed
            assert "MICRO-PROFILE" in composed.upper()
    finally:
        monkeypatch.delenv("PKS_CYBER_PROFILE", raising=False)
        monkeypatch.delenv("PKS_CYBER_PROFILE_MODE", raising=False)


@pytest.mark.parametrize("mode", ("full", "lite", "off"))
def test_rendered_prompt_has_one_large_file_protocol(
    mode: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PKS_CYBER_PROFILE", "true")
    monkeypatch.setenv("PKS_CYBER_PROFILE_MODE", mode)
    monkeypatch.setenv("PKS_ENV_CONTEXT", "false")
    monkeypatch.setenv("PKS_BLACKBOARD", "false")
    agent = SimpleNamespace(
        name="CTF agent",
        model=SimpleNamespace(_current_plan=None),
    )
    run_context = SimpleNamespace(context_variables={})

    rendered = create_system_prompt_renderer(
        "AGENT_BASE_MARKER",
        cyber_micro_profile_key="ctf",
    )(run_context, agent)

    assert rendered.count("LARGE FILE HANDLING & TRUNCATION PROTOCOL") == 1
    assert "AGENT_BASE_MARKER" in rendered
    assert str(Path.home()) in rendered
    assert "Decision Log" not in rendered


def test_lite_reasoner_prompt_does_not_require_a_tool_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PKS_CYBER_PROFILE", "true")
    monkeypatch.setenv("PKS_CYBER_PROFILE_MODE", "lite")
    monkeypatch.setenv("PKS_ENV_CONTEXT", "false")
    monkeypatch.setenv("PKS_BLACKBOARD", "false")
    agent = SimpleNamespace(
        name="Reasoner",
        model=SimpleNamespace(_current_plan=None),
    )
    run_context = SimpleNamespace(context_variables={})
    base = load_prompt_template("prompts/system_reasoner_supporter.md")

    rendered = create_system_prompt_renderer(
        base,
        cyber_micro_profile_key="reasoner",
    )(run_context, agent)

    assert "DO NOT execute any commands or make tool calls" in rendered
    assert "EVERY message SHOULD contain a tool call" not in rendered
    assert "Reasoning, reporting, and routing roles may respond without execution" in rendered


def test_master_uses_pks_runtime_policy_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PKS_AVOID_SUDO", "true")
    monkeypatch.setenv("PKS_TOOL_OUTPUT_MAX", "12345")
    monkeypatch.setenv("PKS_ENV_CONTEXT", "false")
    monkeypatch.setenv("PKS_BLACKBOARD", "false")
    agent = SimpleNamespace(
        name="CTF agent",
        model=SimpleNamespace(_current_plan=None),
    )
    run_context = SimpleNamespace(context_variables={})

    rendered = create_system_prompt_renderer("BASE", "ctf")(run_context, agent)

    assert "The operator enabled **PKS_AVOID_SUDO**" in rendered
    assert "current `12345`-character tool-memory limit" in rendered
    assert "CAI_" not in rendered
    assert "Attacker machine information:" not in rendered


def test_master_keeps_authorization_bound_to_each_mission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PKS_ENV_CONTEXT", "false")
    monkeypatch.setenv("PKS_BLACKBOARD", "false")
    agent = SimpleNamespace(
        name="CTF agent",
        model=SimpleNamespace(_current_plan=None),
    )
    run_context = SimpleNamespace(context_variables={})

    rendered = create_system_prompt_renderer("BASE", "ctf")(run_context, agent)

    assert rendered.count("<mission_authorization_contract>") == 1
    assert "Handoffs change task ownership, not scope." in rendered
    assert "must never broaden the current mission" in rendered
    assert "Within explicit mission boundaries, authorization is complete." in rendered
    assert "Never invent scope" in rendered


def test_compacted_memory_migrates_legacy_marker() -> None:
    legacy = (
        "BASE\n\n<cai_compacted_memory>\nOLD SUMMARY\n"
        "</cai_compacted_memory>"
    )

    rendered = _upsert_compacted_memory_block(legacy, "NEW SUMMARY")

    assert "<cai_compacted_memory>" not in rendered
    assert rendered.count("<pks_compacted_memory>") == 1
    assert "OLD SUMMARY" not in rendered
    assert "NEW SUMMARY" in rendered
