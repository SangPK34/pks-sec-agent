"""PKS_CONTINUOUS_OPS_NO_SUDO must never open interactive sudo elevation in workers."""

from __future__ import annotations

import os
from unittest.mock import Mock, patch

from pks.util import interaction, user_prompts
from pks.util.user_prompts import (
    ensure_sudo_credentials,
    prompt_sudo_elevation,
)


def test_prompt_sudo_elevation_returns_none_when_continuous_ops_no_sudo():
    with patch.dict(os.environ, {"PKS_CONTINUOUS_OPS_NO_SUDO": "true"}, clear=False):
        assert prompt_sudo_elevation("ls /root", "/tmp") is None


def test_ensure_sudo_credentials_returns_message_without_prompt_when_continuous_ops_no_sudo():
    with patch.dict(os.environ, {"PKS_CONTINUOUS_OPS_NO_SUDO": "true"}, clear=False):
        out = ensure_sudo_credentials("sudo ls /root", "/tmp", timeout=5, max_attempts=1)
    assert isinstance(out, str)
    assert "PKS_CONTINUOUS_OPS_NO_SUDO" in out
    assert "ls /root" in out


def test_ensure_sudo_credentials_prompts_once_and_reuses_password(monkeypatch):
    read_password = Mock(return_value="secret")
    validate_password = Mock(return_value=(True, False))

    monkeypatch.delenv("PKS_CONTINUOUS_OPS_NO_SUDO", raising=False)
    monkeypatch.setattr(user_prompts, "_validate_cached_creds", lambda _cwd: False)
    monkeypatch.setattr(user_prompts, "_validate_with_password", validate_password)
    monkeypatch.setattr(
        user_prompts, "_read_sudo_password_maybe_timed", read_password
    )
    monkeypatch.setattr(interaction, "is_prompt_abort_requested", lambda: False)
    monkeypatch.setattr(interaction, "clear_prompt_abort_request", lambda: None)

    user_prompts.clear_cached_password()
    try:
        first = ensure_sudo_credentials(
            "sudo id", "/tmp", max_attempts=1
        )
        second = ensure_sudo_credentials(
            "sudo whoami", "/tmp", max_attempts=1
        )
    finally:
        user_prompts.clear_cached_password()

    assert first is None
    assert second is None
    assert read_password.call_count == 1
    assert validate_password.call_count == 2
