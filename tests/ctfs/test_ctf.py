"""
CTF Integration Test

This module tests PKS's ability to solve Capture The Flag (CTF) challenges.
The test runs the PKS CLI with a specified agent and verifies that the flag
is found by checking the CTF_FLAG_FOUND environment variable.

Environment Variables:
    CTF_NAME: Name of the CTF challenge to run (required)
    PKS_AGENT_TYPE: Agent type to use (default: "one_tool_agent")
    PKS_MODEL: Model to use (default: "gpt-5.6-terra")
    CTF_CHALLENGE: Specific challenge within the CTF (optional)

Example:
    CTF_NAME="urgent" PKS_AGENT_TYPE="redteam_agent" pytest -s tests/ctfs/test_ctf.py
"""
import os
import pytest
from pks.cli import run_pks_cli
from pks.agents import get_agent_by_name

@pytest.mark.allow_call_model_methods
@pytest.mark.integration
@pytest.mark.timeout(2400) # 2400 = 40 min*60 s
def test_pks_ctf(monkeypatch):
    """
    Test that running the CLI sets the CTF_FLAG_FOUND environment variable.
    If the test runs for more than 20 minutes, it is forcibly stopped.
    """

    agent_type = os.getenv("PKS_AGENT_TYPE", "one_tool_agent")
    model_name = os.getenv("PKS_MODEL", "gpt-5.6-terra")
    agent = get_agent_by_name(agent_type, agent_id="P1")

    # Configure model for CLI compatibility
    if hasattr(agent, "model"):
        if hasattr(agent.model, "disable_rich_streaming"):
            agent.model.disable_rich_streaming = True
        if hasattr(agent.model, "suppress_final_output"):
            agent.model.suppress_final_output = False

    # Ensure the flag isn't present before test
    monkeypatch.delenv("CTF_FLAG_FOUND", raising=False)
    
    ctf_name = os.environ.get("CTF_NAME", "<not set>")
    ctf_challenge = os.environ.get("CTF_CHALLENGE", "<not set>")
    pks_model = os.environ.get("PKS_MODEL", "<not set>")

    print(
        f" Starting test for CTF_NAME='{ctf_name}', "
        f"CTF_CHALLENGE='{ctf_challenge}', and PKS_MODEL='{pks_model}'."
        )
    
    run_pks_cli(agent, force_until_flag=True)
    
    if "CTF_FLAG_FOUND" in os.environ:
        flag = os.environ["CTF_FLAG_FOUND"]
        print("===========PASSED===========")
        print(f"CTF_FLAG_FOUND value is '{flag}'")
    else:
        print("===========FAILED===========")
        print(f"Flag not found")
    
    assert "CTF_FLAG_FOUND" in os.environ, "CTF flag was not found and test failed"
