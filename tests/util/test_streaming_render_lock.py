from __future__ import annotations

from pks.util import streaming


def test_exclusive_tool_render_pauses_and_resumes_wait_hints(monkeypatch) -> None:
    events: list[str] = []
    monkeypatch.setattr(
        "pks.util.wait_hints.pause_all_wait_hints",
        lambda: events.append("pause"),
    )
    monkeypatch.setattr(
        "pks.util.wait_hints.resume_all_wait_hints",
        lambda: events.append("resume"),
    )

    with streaming._exclusive_tool_render():
        events.append("render")

    assert events == ["pause", "render", "resume"]
