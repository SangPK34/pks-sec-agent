from pks.sdk.agents.simple_agent_manager import SimpleAgentManager


def test_shared_context_uses_latest_exchange_and_bounds_long_response():
    manager = SimpleAgentManager()
    history = []
    for index in range(4):
        history.extend(
            [
                {"role": "user", "content": f"question-{index}"},
                {
                    "role": "assistant",
                    "content": f"response-{index}-" + ("x" * 3000),
                },
            ]
        )

    manager.extract_shareable_context("Bug Bounter", history)
    shared = manager.get_shared_context_injection()

    assert "question-0" not in shared
    assert "question-2" in shared
    assert "question-3" in shared
    assert "[shared response clipped]" in shared
