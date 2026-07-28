from __future__ import annotations

import os

import pytest

from pks.model_catalog import MODELS, api_model_id, find_model
from pks.repl.commands.base import Command
from pks.repl.commands.model import EffortCommand, ModelCommand


@pytest.fixture(autouse=True)
def restore_model_environment():
    original_model = os.environ.get("PKS_MODEL")
    original_effort = os.environ.get("PKS_REASONING_EFFORT")
    yield
    if original_model is None:
        os.environ.pop("PKS_MODEL", None)
    else:
        os.environ["PKS_MODEL"] = original_model
    if original_effort is None:
        os.environ.pop("PKS_REASONING_EFFORT", None)
    else:
        os.environ["PKS_REASONING_EFFORT"] = original_effort


def test_command_initialization():
    command = ModelCommand()
    assert isinstance(command, Command)
    assert command.name == "/model"
    assert command.aliases == ["/mod"]
    assert command.cached_models == [model.model_id for model in MODELS]


def test_catalog_keeps_local_cai_alias_and_frontier_models():
    cai = find_model("openai/CAI")
    assert cai is not None
    assert cai.context_tokens == 1_000_000
    assert find_model("deepseek/deepseek-v4-flash") is not None
    assert find_model("deepseek/deepseek-v4-pro") is not None
    assert find_model("gpt-5.6-terra") is not None


def test_local_cai_alias_uses_gateway_model_id():
    assert api_model_id("openai/CAI") == "CAI"
    assert api_model_id("my-gateway/custom-model") == "my-gateway/custom-model"


def test_select_catalog_model_by_name():
    command = ModelCommand()
    assert command.handle(["deepseek/deepseek-v4-flash"]) is True
    assert os.environ["PKS_MODEL"] == "deepseek/deepseek-v4-flash"


def test_select_catalog_model_by_number():
    command = ModelCommand()
    assert command.handle(["1"]) is True
    assert os.environ["PKS_MODEL"] == MODELS[0].model_id


def test_custom_gateway_model_id_is_accepted():
    command = ModelCommand()
    assert command.handle(["my-gateway/custom-model"]) is True
    assert os.environ["PKS_MODEL"] == "my-gateway/custom-model"


def test_invalid_model_number_does_not_change_model():
    os.environ["PKS_MODEL"] = "openai/CAI"
    command = ModelCommand()
    assert command.handle(["9999"]) is True
    assert os.environ["PKS_MODEL"] == "openai/CAI"


def test_show_and_search_are_local_only():
    command = ModelCommand()
    assert command.handle([]) is True
    assert command.handle(["show"]) is True
    assert command.handle(["show", "deepseek"]) is True


def test_effort_is_set_and_disabled():
    os.environ["PKS_MODEL"] = "openai/CAI"
    command = EffortCommand()
    assert command.handle(["high"]) is True
    assert os.environ["PKS_REASONING_EFFORT"] == "high"
    assert command.handle(["off"]) is True
    assert "PKS_REASONING_EFFORT" not in os.environ


def test_unsupported_effort_is_rejected_for_catalog_model():
    os.environ["PKS_MODEL"] = "openai/CAI"
    os.environ.pop("PKS_REASONING_EFFORT", None)
    command = EffortCommand()
    assert command.handle(["low"]) is True
    assert "PKS_REASONING_EFFORT" not in os.environ


def test_switch_clears_incompatible_effort():
    os.environ["PKS_MODEL"] = "gpt-5.6-terra"
    os.environ["PKS_REASONING_EFFORT"] = "medium"
    command = ModelCommand()
    assert command.handle(["moonshotai/Kimi-K3"]) is True
    assert "PKS_REASONING_EFFORT" not in os.environ
