"""Replay Attack and Counteroffensive Agent
Specialized agent module focused on network replay attacks, packet manipulation,
and counteroffensive techniques for security testing and incident response.
This agent specializes in:
- Network packet capture and analysis
- Traffic replay attacks against various protocols
- Authentication sequence and session token replay
- Traffic manipulation and injection
- Man-in-the-middle attack simulation
- TCP session hijacking
- Protocol exploitation techniques
- Anti-replay defense testing
Objectives:
- Identify and exploit replay vulnerabilities
- Test protocol implementation security
- Simulate advanced persistent threats
- Evaluate defensive controls against replay attacks
"""

from openai import AsyncOpenAI
from pks.sdk.agents import Agent, OpenAIChatCompletionsModel  # pylint: disable=import-error
from pks.util import load_prompt_template, create_system_prompt_renderer
from pks.config import get_config
from dotenv import load_dotenv
from pks.tools.command_and_control.sshpass import (  # pylint: disable=import-error # noqa: E501
    run_ssh_command_with_credentials,
)

from pks.tools.reconnaissance.generic_linux_command import (  # pylint: disable=import-error # noqa: E501
generic_linux_command,
)

from pks.tools.reconnaissance.exec_code import (  # pylint: disable=import-error # noqa: E501
    execute_code,
)
from pks.tools.web.search_web import (  # pylint: disable=import-error # noqa: E501
    make_web_search_with_explanation,
)

# Import network tools
from pks.tools.network.capture_traffic import (  # pylint: disable=import-error # noqa: E501
    capture_remote_traffic,
    remote_capture_session,
)

load_dotenv()
_cfg = get_config()

# Prompts
replay_attack_agent_prompt = load_prompt_template("prompts/system_replay_attack_agent.md")

# Define tools list based on available API keys (via PKSConfig) [S]
tools = [
    generic_linux_command,
    run_ssh_command_with_credentials,
    execute_code,
    capture_remote_traffic,
    remote_capture_session,
]

# Add conditional tools based on available API keys [S]
if _cfg.perplexity_api_key:
    tools.append(make_web_search_with_explanation)


# Create the agent instance
replay_attack_agent = Agent(
    name="Replay Attack Agent",
    instructions=create_system_prompt_renderer(
        replay_attack_agent_prompt,
        cyber_micro_profile_key="replay",
    ),
    description="""Agent that specializes in network replay attacks and counteroffensive techniques.
                   Expert in packet manipulation, traffic replay, and protocol exploitation.""",
    model=OpenAIChatCompletionsModel(
        model=_cfg.model,
        openai_client=AsyncOpenAI(),
    ),
    tools=tools,
)
