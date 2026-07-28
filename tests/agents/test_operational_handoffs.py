from openai.types.responses import ResponseFunctionToolCall

from pks.agents.operational_handoffs import handoff_task_filter
from pks.sdk.agents import Agent, HandoffInputData
from pks.sdk.agents.items import HandoffCallItem


def test_handoff_task_is_preserved_as_specialist_input():
    agent = Agent(name="Root Agent")
    call = HandoffCallItem(
        agent=agent,
        raw_item=ResponseFunctionToolCall(
            arguments='{"task":"Inspect /tmp/sample with file and wc first."}',
            call_id="call-1",
            name="transfer_to_ctf_agent",
            type="function_call",
        ),
    )
    data = HandoffInputData(
        input_history="Kiểm tra file này",
        pre_handoff_items=(),
        new_items=(call,),
    )

    filtered = handoff_task_filter(data)

    assert isinstance(filtered.input_history, str)
    assert "Inspect /tmp/sample with file and wc first." in filtered.input_history
    assert "original operator request remains canonical" in filtered.input_history
    assert "authoritative for this turn" not in filtered.input_history
    assert filtered.new_items == ()
