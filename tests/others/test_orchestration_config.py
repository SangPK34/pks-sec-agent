"""Configuration defaults for the orchestration agent."""

from __future__ import annotations

from pks.config import PKSConfig, reset_config


def test_default_agent_type_is_root_agent(monkeypatch):
    monkeypatch.delenv("PKS_AGENT_TYPE", raising=False)
    reset_config()

    cfg = PKSConfig.from_env()

    assert cfg.agent_type == "root_agent"


def test_selection_agent_env_alias_resolves_to_root(monkeypatch):
    monkeypatch.setenv("PKS_AGENT_TYPE", "selection_agent")
    reset_config()
    assert PKSConfig.from_env().agent_type == "root_agent"


def test_orchestration_worker_max_turns_default(monkeypatch):
    monkeypatch.delenv("PKS_ORCHESTRATION_WORKER_MAX_TURNS", raising=False)
    reset_config()
    assert PKSConfig.from_env().orchestration_worker_max_turns == 6


def test_orchestration_worker_max_turns_env(monkeypatch):
    monkeypatch.setenv("PKS_ORCHESTRATION_WORKER_MAX_TURNS", "12")
    reset_config()
    assert PKSConfig.from_env().orchestration_worker_max_turns == 12


def test_orchestration_mas_hint_default(monkeypatch):
    monkeypatch.delenv("PKS_ORCHESTRATION_MAS_HINT", raising=False)
    reset_config()
    assert PKSConfig.from_env().orchestration_mas_hint is True


def test_orchestration_mas_hint_false(monkeypatch):
    monkeypatch.setenv("PKS_ORCHESTRATION_MAS_HINT", "false")
    reset_config()
    assert PKSConfig.from_env().orchestration_mas_hint is False
