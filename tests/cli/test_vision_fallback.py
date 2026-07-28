from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

from pks import cli_headless
from pks.util.vision import PreparedImage, PreparedVisionInput


def test_headless_retries_once_with_ocr_after_vision_rejection(
    monkeypatch, tmp_path: Path
) -> None:
    image_path = tmp_path / "flag.png"
    image_path.touch()
    data_url = "data:image/png;base64,AAAA"
    prepared = PreparedVisionInput(
        original_text=f"inspect {image_path}",
        model_input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": f"inspect {image_path}"},
                    {
                        "type": "input_image",
                        "image_url": data_url,
                        "detail": "auto",
                    },
                ],
            }
        ],
        images=(PreparedImage(image_path, data_url),),
    )
    agent = SimpleNamespace(name="Root Agent")
    console = SimpleNamespace(print=lambda *_args, **_kwargs: None)
    calls = []
    removed = []
    compacted = []

    def fake_run(_agent, model_input, *_args):
        calls.append(model_input)
        if len(calls) == 1:
            raise RuntimeError("input_image is not supported")
        return SimpleNamespace(last_agent=agent)

    monkeypatch.setattr(cli_headless, "_get_config", lambda: SimpleNamespace(stream=True))
    monkeypatch.setattr(
        cli_headless,
        "prepare_agent_vision_input",
        lambda _text, _agent: prepared,
    )
    monkeypatch.setattr(cli_headless, "_run_streamed", fake_run)
    monkeypatch.setattr(
        cli_headless,
        "remove_pending_vision_history",
        lambda *_args: removed.append(True),
    )
    monkeypatch.setattr(
        cli_headless,
        "compact_vision_history",
        lambda *_args: compacted.append(True),
    )
    monkeypatch.setattr(
        PreparedVisionInput,
        "ocr_fallback_input",
        lambda _self: "OCR fallback evidence",
    )
    monkeypatch.setattr(
        "pks.repl.ui.compact_wiring.turn_lifecycle",
        lambda **_kwargs: nullcontext(),
    )

    cli_headless._run_single_agent(
        agent,
        prepared.original_text,
        console,
        force_until_flag=False,
        ctf_global=None,
    )

    assert calls == [prepared.model_input, "OCR fallback evidence"]
    assert removed == [True]
    assert compacted == [True]
