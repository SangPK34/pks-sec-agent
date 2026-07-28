#!/usr/bin/env python3
"""
Tests for ``env_catalog`` (used by ``/env``) and deprecated ``ConfigCommand`` (``/config``).
Catalog mutations use EnvCommand for list/get/set via ``/env set``.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from pks.repl.commands.base import Command
from pks.repl.commands.config import ConfigCommand
from pks.repl.commands.env_catalog import (
    ENV_VARS,
    get_env_var_value,
    handle_env_catalog_default,
    handle_env_catalog_get,
    handle_env_catalog_list,
    handle_env_catalog_set,
    set_env_var,
)
from pks.repl.commands.env_catalog_validate import sample_valid_test_value
from pks.repl.commands.env_info_catalog import is_restart_required
from pks.repl.commands.env import EnvCommand


def get_var_number(var_name: str) -> str:
    """Helper to find the ENV_VARS index for a given variable name."""
    for num, var_info in ENV_VARS.items():
        if var_info["name"] == var_name:
            return str(num)
    raise ValueError(f"Variable {var_name} not found in ENV_VARS")


class TestConfigCommandDeprecated:
    """/config is a deprecated no-op stub."""

    @pytest.fixture
    def config_command(self):
        return ConfigCommand()

    def test_command_initialization(self, config_command):
        assert config_command.name == "/config"
        assert "Deprecated" in config_command.description
        assert config_command.aliases == ["/cfg"]
        assert config_command.get_subcommands() == []

    def test_handle_always_deprecation(self, config_command):
        assert config_command.handle([]) is True
        assert config_command.handle(["list"]) is True
        # Args ignored; avoid a catalog index that could be mistaken for a live /env row.
        assert config_command.handle(["set", "99", "x"]) is True


class TestEnvCatalogHandlers:
    """Catalog list/get/set via module functions (used by /env)."""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        os.environ["PKS_TELEMETRY"] = "false"
        os.environ["PKS_TRACING"] = "false"

        self.original_env_vars = {}
        for var_info in ENV_VARS.values():
            var_name = var_info["name"]
            if var_name in os.environ:
                self.original_env_vars[var_name] = os.environ[var_name]

        yield

        for var_info in ENV_VARS.values():
            var_name = var_info["name"]
            if var_name in self.original_env_vars:
                os.environ[var_name] = self.original_env_vars[var_name]
            elif var_name in os.environ:
                del os.environ[var_name]

    def test_env_vars_structure(self):
        assert isinstance(ENV_VARS, dict)
        assert len(ENV_VARS) > 0

        for num, var_info in ENV_VARS.items():
            assert isinstance(num, int)
            assert "name" in var_info
            assert "description" in var_info
            assert "default" in var_info

            assert isinstance(var_info["name"], str)
            assert isinstance(var_info["description"], str)
            assert var_info["default"] is None or isinstance(var_info["default"], str)

    def test_get_env_var_value_with_set_value(self):
        os.environ["PKS_MODEL"] = "test-model"

        result = get_env_var_value("PKS_MODEL")
        assert result == "test-model"

    def test_get_env_var_value_with_default(self):
        if "PKS_MODEL" in os.environ:
            del os.environ["PKS_MODEL"]

        result = get_env_var_value("PKS_MODEL")
        expected_default = None
        for var_info in ENV_VARS.values():
            if var_info["name"] == "PKS_MODEL":
                expected_default = var_info["default"]
                break

        assert result == (expected_default or "Not set")

    def test_get_env_var_value_unknown_variable(self):
        result = get_env_var_value("UNKNOWN_VARIABLE")
        assert result == "Unknown variable"

    def test_set_env_var(self):
        result = set_env_var("TEST_VAR", "test_value")
        assert result is True
        assert os.environ.get("TEST_VAR") == "test_value"

        if "TEST_VAR" in os.environ:
            del os.environ["TEST_VAR"]

    def test_handle_list(self):
        assert handle_env_catalog_list([]) is True

    def test_handle_get_valid_number(self):
        var_num = get_var_number("PKS_MODEL")
        assert handle_env_catalog_get([var_num]) is True

    def test_handle_get_valid_name(self):
        assert handle_env_catalog_get(["PKS_MODEL"]) is True

    def test_handle_get_invalid_number(self):
        assert handle_env_catalog_get(["999"]) is False

    def test_handle_get_unknown_name(self):
        assert handle_env_catalog_get(["not_a_number"]) is False

    def test_handle_get_no_args(self):
        assert handle_env_catalog_get([]) is False

    def test_handle_set_valid_number_and_value(self):
        var_num = get_var_number("PKS_MODEL")
        assert handle_env_catalog_set([var_num, "gpt-5.6-terra"]) is True
        assert os.environ.get("PKS_MODEL") == "gpt-5.6-terra"

    def test_handle_set_invalid_number(self):
        assert handle_env_catalog_set(["999", "some_value"]) is False

    def test_handle_set_unknown_spec(self):
        assert handle_env_catalog_set(["not_a_number", "some_value"]) is False

    def test_handle_set_no_args(self):
        assert handle_env_catalog_set([]) is False

    def test_handle_set_insufficient_args(self):
        var_num = get_var_number("PKS_MODEL")
        assert handle_env_catalog_set([var_num]) is False

    def test_handle_set_with_spaces_in_value(self):
        var_num = get_var_number("PKS_PATTERN_DESCRIPTION")
        assert handle_env_catalog_set([var_num, "hello", "world"]) is True
        assert os.environ.get("PKS_PATTERN_DESCRIPTION") == "hello world"

    def test_handle_set_empty_value(self):
        var_num = get_var_number("PKS_MODEL")
        assert handle_env_catalog_set([var_num, ""]) is False

    def test_handle_set_ctf_ip_rejects_invalid(self):
        ip_num = get_var_number("CTF_IP")
        assert handle_env_catalog_set([ip_num, "not-an-ip"]) is False

    def test_handle_set_ctf_name_rejects_unknown_when_pksbench_has_list(self):
        from pks.repl.commands.env_catalog_validate import _load_pksbench_ctf_names_lowercase

        if not _load_pksbench_ctf_names_lowercase():
            pytest.skip("PKSBench CTF config not available")

        var_num = get_var_number("CTF_NAME")
        prev = os.environ.get("CTF_NAME")
        try:
            assert handle_env_catalog_set([var_num, "___not_a_real_ctf_name_xyz___"]) is False
        finally:
            if prev is not None:
                os.environ["CTF_NAME"] = prev
            else:
                os.environ.pop("CTF_NAME", None)

    def test_handle_env_catalog_default(self):
        os.environ["PKS_DEBUG"] = "2"
        assert handle_env_catalog_default([]) is True
        assert os.environ.get("PKS_DEBUG") == "1"

    def test_specific_env_vars_exist(self):
        important_vars = [
            "PKS_MODEL",
            "PKS_DEBUG",
            "PKS_BRIEF",
            "PKS_MAX_TURNS",
            "PKS_TRACING",
            "PKS_AGENT_TYPE",
            "CTF_NAME",
            "CTF_CHALLENGE",
            "PKS_MERGE_SUMMARIZE_PER_WORKER",
            "OPENAI_API_KEY",
        ]

        defined_var_names = [var_info["name"] for var_info in ENV_VARS.values()]

        for var_name in important_vars:
            assert var_name in defined_var_names, f"{var_name} should be defined in ENV_VARS"

    def test_env_var_defaults_are_reasonable(self):
        for var_info in ENV_VARS.values():
            var_name = var_info["name"]
            default = var_info["default"]

            boolean_keywords = [
                "debug",
                "brief",
                "tracing",
                "online",
                "offline",
                "inside",
            ]
            non_boolean_patterns = ["interval", "collection", "model"]
            if (
                any(keyword in var_name.lower() for keyword in boolean_keywords)
                and not any(pattern in var_name.lower() for pattern in non_boolean_patterns)
            ):
                if default is not None:
                    valid_values = ["true", "false", "0", "1", "2"]
                    assert (
                        default.lower() in valid_values
                    ), f"{var_name} should have boolean-like or numeric default"

            if any(keyword in var_name.lower() for keyword in ["turns", "limit", "interval"]):
                if default is not None:
                    try:
                        float(default)
                    except ValueError:
                        assert default == "inf", f"{var_name} should have numeric default or 'inf'"


class TestEnvCommandRouting:
    """Integration-style routing on EnvCommand."""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        os.environ["PKS_TELEMETRY"] = "false"
        os.environ["PKS_TRACING"] = "false"

        self.original_env_vars = {}
        for var_info in ENV_VARS.values():
            var_name = var_info["name"]
            if var_name in os.environ:
                self.original_env_vars[var_name] = os.environ[var_name]

        yield

        for var_info in ENV_VARS.values():
            var_name = var_info["name"]
            if var_name in self.original_env_vars:
                os.environ[var_name] = self.original_env_vars[var_name]
            elif var_name in os.environ:
                del os.environ[var_name]

    @pytest.fixture
    def env_command(self):
        return EnvCommand()

    def test_command_base_functionality(self, env_command):
        assert isinstance(env_command, Command)
        assert env_command.name == "/env"
        assert "/e" in env_command.aliases

    def test_handle_main_command_routing(self, env_command):
        var_num = get_var_number("PKS_MODEL")

        assert env_command.handle(["list"]) is True

        assert env_command.handle(["get", var_num]) is True

        assert env_command.handle(["set", var_num, "gpt-5.6-terra"]) is True
        assert os.environ.get("PKS_MODEL") == "gpt-5.6-terra"

    def test_handle_unknown_subcommand(self, env_command):
        assert env_command.handle(["unknown_subcommand"]) is False


@pytest.mark.integration
class TestEnvCommandIntegration:
    """Integration tests for /env catalog workflow."""

    @pytest.fixture(autouse=True)
    def setup_integration(self):
        self.original_env_vars = {}
        for var_info in ENV_VARS.values():
            var_name = var_info["name"]
            if var_name in os.environ:
                self.original_env_vars[var_name] = os.environ[var_name]

        yield

        for var_info in ENV_VARS.values():
            var_name = var_info["name"]
            if var_name in self.original_env_vars:
                os.environ[var_name] = self.original_env_vars[var_name]
            elif var_name in os.environ:
                del os.environ[var_name]

    def test_full_env_workflow(self):
        cmd = EnvCommand()
        var_num = get_var_number("PKS_MODEL")

        assert cmd.handle(["list"]) is True

        assert cmd.handle(["get", var_num]) is True

        assert cmd.handle(["set", var_num, "openai/CAI"]) is True
        assert os.environ.get("PKS_MODEL") == "openai/CAI"

        assert cmd.handle(["get", var_num]) is True

        for var_info in ENV_VARS.values():
            if var_info["name"] == "PKS_MODEL" and var_info["default"]:
                assert cmd.handle(["set", var_num, str(var_info["default"])]) is True
                break

    def test_multiple_variable_modifications(self):
        cmd = EnvCommand()

        modifications = [
            (get_var_number("PKS_MODEL"), "gpt-5.6-terra", "PKS_MODEL"),
            (get_var_number("PKS_DEBUG"), "2", "PKS_DEBUG"),
            (get_var_number("PKS_BRIEF"), "true", "PKS_BRIEF"),
        ]

        for var_num, value, var_name in modifications:
            assert cmd.handle(["set", var_num, value]) is True
            assert cmd.handle(["get", var_num]) is True

        for _, expected_value, var_name in modifications:
            assert os.environ.get(var_name) == expected_value

    def test_edge_case_values(self):
        cmd = EnvCommand()
        model_num = get_var_number("PKS_MODEL")
        debug_num = get_var_number("PKS_DEBUG")

        pat_num = get_var_number("PKS_PATTERN_DESCRIPTION")
        assert cmd.handle(["set", pat_num, "x", "y", "z"]) is True
        assert os.environ.get("PKS_PATTERN_DESCRIPTION") == "x y z"

        assert cmd.handle(["set", model_num, "gpt-5.6-terra"]) is True
        assert cmd.handle(["set", model_num, "local/custom-model"]) is True
        assert os.environ.get("PKS_MODEL") == "local/custom-model"
        assert cmd.handle(["set", model_num, ""]) is False

        assert cmd.handle(["set", debug_num, "0"]) is True
        assert os.environ.get("PKS_DEBUG") == "0"
        assert cmd.handle(["set", debug_num, "999"]) is False

    def test_all_env_vars_can_be_set_and_retrieved(self):
        cmd = EnvCommand()

        for var_num, var_info in ENV_VARS.items():
            var_name = str(var_info["name"])
            test_value = sample_valid_test_value(var_name, var_info)

            if is_restart_required(var_name):
                assert cmd.handle(["set", str(var_num), test_value]) is False, (
                    f"/env set should refuse locked-at-startup {var_name}"
                )
                assert cmd.handle(["get", str(var_num)]) is True, f"Failed to get {var_name}"
                continue

            assert cmd.handle(["set", str(var_num), test_value]) is True, f"Failed to set {var_name}"
            assert cmd.handle(["get", str(var_num)]) is True, f"Failed to get {var_name}"
            assert os.environ.get(var_name) == test_value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
