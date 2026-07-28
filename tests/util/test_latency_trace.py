import json

from pks.util import latency_trace


def test_latency_trace_records_monotonic_stages_and_resets_context(
    monkeypatch,
    tmp_path,
):
    trace_file = tmp_path / "latency.jsonl"
    monkeypatch.setenv("PKS_LATENCY_TRACE", "1")
    monkeypatch.setenv("PKS_LATENCY_TRACE_FILE", str(trace_file))

    trace, token = latency_trace.begin_latency_trace("CTF agent", "tool_result")
    try:
        latency_trace.mark_latency("first_provider_event", once=True)
        latency_trace.mark_latency("first_provider_event", once=True)
        latency_trace.mark_latency("first_text_delta", once=True)
        latency_trace.mark_latency("first_ui_render", once=True)
        latency_trace.mark_latency("response_complete", once=True)
    finally:
        latency_trace.end_latency_trace(token)

    records = [
        json.loads(line)
        for line in trace_file.read_text(encoding="utf-8").splitlines()
    ]
    assert [record["event"] for record in records] == [
        "continuation_request_start",
        "first_provider_event",
        "first_text_delta",
        "first_ui_render",
        "response_complete",
    ]
    assert all(record["trace_id"] == trace.trace_id for record in records)
    assert all(record["monotonic"] >= trace.started_at for record in records)
    assert latency_trace._CURRENT_TRACE.get() is None
