import datetime

from prompt_toolkit.formatted_text import HTML, to_formatted_text

from pks.repl.ui import toolbar


def _plain(value) -> str:
    return "".join(fragment[1] for fragment in to_formatted_text(value))


def test_context_refreshes_immediately_from_environment(monkeypatch):
    monkeypatch.setitem(
        toolbar.toolbar_cache,
        "html",
        HTML(
            "<ansiyellow>Model:</ansiyellow> CAI | "
            "<ansicyan>Context:</ansicyan> <ansigreen>0.0%</ansigreen>"
        ),
    )
    monkeypatch.setitem(toolbar.toolbar_cache, "context_env", "0")
    monkeypatch.setitem(
        toolbar.toolbar_cache,
        "last_update",
        datetime.datetime.now(),
    )
    monkeypatch.setenv("PKS_CONTEXT_USAGE", "0.0125")

    assert "Context: 1.2%" in _plain(toolbar.get_toolbar_with_refresh())


def test_tiny_nonzero_context_is_not_rendered_as_zero():
    assert toolbar._format_context_usage("0.0005") == "<0.1%"
