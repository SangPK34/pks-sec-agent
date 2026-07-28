"""Root Agent for PKS — direct utility execution plus specialist routing."""

from __future__ import annotations

from dotenv import load_dotenv
from openai import AsyncOpenAI

from pks.agents.guardrails import get_security_guardrails
from pks.agents.operational_handoffs import build_operational_handoffs
from pks.config import get_config
from pks.sdk.agents import Agent, OpenAIChatCompletionsModel
from pks.tools.misc.agent_discovery import (
    analyze_task_requirements,
    check_available_agents,
    get_agent_number,
)
from pks.tools.reconnaissance.generic_linux_command import generic_linux_command
from pks.tools.web.search_web import make_web_search_with_explanation
from pks.util import create_system_prompt_renderer, load_prompt_template

load_dotenv()
_cfg = get_config()

root_agent_system_prompt = load_prompt_template("prompts/system_root_agent.md")

tools = [
    generic_linux_command,
    check_available_agents,
    analyze_task_requirements,
    get_agent_number,
]

if _cfg.perplexity_api_key:
    tools.append(make_web_search_with_explanation)

input_guardrails, output_guardrails = get_security_guardrails()

root_agent = Agent(
    name="Root Agent",
    description=(
        "Default PKS entry agent: executes short shell/file utility tasks directly "
        "and routes specialist cybersecurity work through handoffs."
    ),
    instructions=create_system_prompt_renderer(
        root_agent_system_prompt,
        cyber_micro_profile_key="root",
    ),
    tools=tools,
    handoffs=build_operational_handoffs(),
    input_guardrails=input_guardrails,
    output_guardrails=output_guardrails,
    tool_use_behavior="run_llm_again",
    reset_tool_choice=True,
    model=OpenAIChatCompletionsModel(
        model=_cfg.model,
        openai_client=AsyncOpenAI(),
        agent_name="Root Agent",
        agent_type="root_agent",
    ),
)


def transfer_to_root_agent(**kwargs):  # pylint: disable=W0613
    """Hand control back to the root agent."""
    return root_agent
