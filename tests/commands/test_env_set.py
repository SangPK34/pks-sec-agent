"""
Tests for /env set / get / default (catalog by name or number).
"""
from __future__ import annotations

import os


def _tool_output_limit_index() -> str:
    from pks.repl.commands.env_catalog import ENV_VARS

    for num, var_info in ENV_VARS.items():
        if var_info["name"] == "PKS_TOOL_OUTPUT_MAX":
            return str(num)
    raise AssertionError("PKS_TOOL_OUTPUT_MAX not in ENV_VARS")


class TestEnvSetSyntax:
    """/env set only via subcommand."""

    def test_env_set_by_name(self):
        from pks.repl.commands.env import EnvCommand

        cmd = EnvCommand()
        original = os.environ.get("PKS_TOOL_OUTPUT_MAX")
        try:
            assert cmd.handle(["set", "PKS_TOOL_OUTPUT_MAX", "20000"]) is True
            assert os.environ.get("PKS_TOOL_OUTPUT_MAX") == "20000"
        finally:
            if original:
                os.environ["PKS_TOOL_OUTPUT_MAX"] = original
            elif "PKS_TOOL_OUTPUT_MAX" in os.environ:
                del os.environ["PKS_TOOL_OUTPUT_MAX"]

    def test_env_set_by_number(self):
        from pks.repl.commands.env import EnvCommand

        cmd = EnvCommand()
        original = os.environ.get("PKS_TOOL_OUTPUT_MAX")
        idx = _tool_output_limit_index()
        try:
            assert cmd.handle(["set", idx, "24000"]) is True
            assert os.environ.get("PKS_TOOL_OUTPUT_MAX") == "24000"
        finally:
            if original:
                os.environ["PKS_TOOL_OUTPUT_MAX"] = original
            elif "PKS_TOOL_OUTPUT_MAX" in os.environ:
                del os.environ["PKS_TOOL_OUTPUT_MAX"]

    def test_env_set_value_with_spaces(self):
        from pks.repl.commands.env import EnvCommand

        cmd = EnvCommand()
        original = os.environ.get("PKS_PATTERN_DESCRIPTION")
        try:
            assert cmd.handle(["set", "PKS_PATTERN_DESCRIPTION", "hello", "world"]) is True
            assert os.environ.get("PKS_PATTERN_DESCRIPTION") == "hello world"
        finally:
            if original:
                os.environ["PKS_PATTERN_DESCRIPTION"] = original
            elif "PKS_PATTERN_DESCRIPTION" in os.environ:
                del os.environ["PKS_PATTERN_DESCRIPTION"]

    def test_env_rejects_unknown_at_root(self):
        from pks.repl.commands.env import EnvCommand

        cmd = EnvCommand()
        assert cmd.handle(["UNKNOWN_VAR=123"]) is False

    def test_env_rejects_unknown_set(self):
        from pks.repl.commands.env import EnvCommand

        assert EnvCommand().handle(["set", "NOT_A_VAR", "x"]) is False

    def test_tool_output_limit_validation(self):
        from pks.repl.commands.env_catalog import ENV_VARS
        from pks.repl.commands.env_catalog_validate import validate_catalog_value

        var_info = next(
            info
            for info in ENV_VARS.values()
            if info["name"] == "PKS_TOOL_OUTPUT_MAX"
        )

        assert validate_catalog_value("PKS_TOOL_OUTPUT_MAX", "800", var_info) is None
        assert validate_catalog_value("PKS_TOOL_OUTPUT_MAX", "799", var_info) is not None
