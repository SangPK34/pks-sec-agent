from __future__ import annotations

import os

from pks.cli_setup import load_dotenv_and_defaults


def test_project_dotenv_overrides_parent_process_credentials(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        'OPENAI_API_KEY="project-key"\n'
        'OPENAI_BASE_URL="http://localhost:20128/v1"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "parent-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    load_dotenv_and_defaults()

    assert os.environ["OPENAI_API_KEY"] == "project-key"
    assert os.environ["OPENAI_BASE_URL"] == "http://localhost:20128/v1"
