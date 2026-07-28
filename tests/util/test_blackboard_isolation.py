from pathlib import Path

from pks.util import blackboard


def _reset_runtime_path() -> None:
    blackboard._RUNTIME_PATH = None
    blackboard._RUNTIME_PID = None


def test_default_blackboard_is_isolated_by_process(monkeypatch, tmp_path):
    monkeypatch.delenv("PKS_BB_FILE", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    _reset_runtime_path()

    monkeypatch.setattr(blackboard.os, "getpid", lambda: 4101)
    first = blackboard._bb_path()
    monkeypatch.setattr(blackboard.os, "getpid", lambda: 4102)
    second = blackboard._bb_path()

    assert first == tmp_path / ".pks" / "runtime" / "blackboard-4101.json"
    assert second == tmp_path / ".pks" / "runtime" / "blackboard-4102.json"
    assert first != second


def test_agents_in_same_process_share_blackboard(monkeypatch, tmp_path):
    monkeypatch.delenv("PKS_BB_FILE", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(blackboard.os, "getpid", lambda: 4103)
    _reset_runtime_path()

    assert blackboard._bb_path() == blackboard._bb_path()


def test_explicit_blackboard_path_is_preserved(monkeypatch, tmp_path):
    explicit = tmp_path / "shared" / "board.json"
    monkeypatch.setenv("PKS_BB_FILE", str(explicit))
    _reset_runtime_path()

    assert blackboard._bb_path() == explicit


def test_cleanup_removes_only_runtime_blackboard(monkeypatch, tmp_path):
    monkeypatch.delenv("PKS_BB_FILE", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(blackboard.os, "getpid", lambda: 4104)
    _reset_runtime_path()

    board_path = blackboard._bb_path()
    board_path.write_text("{}", encoding="utf-8")
    unrelated = Path(tmp_path) / ".pks" / "blackboard.json"
    unrelated.write_text("{}", encoding="utf-8")

    blackboard._cleanup_runtime_file()

    assert not board_path.exists()
    assert unrelated.exists()
