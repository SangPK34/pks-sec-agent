"""Selection Agent for PKS — handoff-based router.

Routes user work to specialized agents via SDK **handoffs**: the picked
specialist takes over the session. When ``PKS_AGENT_ROUTE_MODE=auto`` each
operational request is delegated with a ``transfer_to_*`` tool. Users can pin a
specialist with ``/agent select <other>`` (sets ``PKS_AGENT_ROUTE_MODE=pinned``).

Distinct from :mod:`pks.agents.orchestration_agent` (the default entry agent
since v1.0.6), which keeps control of the session and invokes specialists as
worker tools instead of handing off.
"""

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
from pks.tools.web.search_web import make_web_search_with_explanation
from pks.util import create_system_prompt_renderer, load_prompt_template

load_dotenv()
_cfg = get_config()

selection_agent_system_prompt = load_prompt_template("prompts/system_selection_agent.md")

# Discovery tools — for meta questions. Operational work uses handoffs.
tools = [
    check_available_agents,
    analyze_task_requirements,
    get_agent_number,
]

if _cfg.perplexity_api_key:
    tools.append(make_web_search_with_explanation)

input_guardrails, output_guardrails = get_security_guardrails()

selection_agent = Agent(
    name="Selection Agent",
    description="""Orchestrator: routes cybersecurity work to the best PKS specialist via handoffs,
or answers pure meta-questions about which agent to use.""",
    instructions=create_system_prompt_renderer(
        selection_agent_system_prompt,
        cyber_micro_profile_key="selection",
    ),
    tools=tools,
    handoffs=build_operational_handoffs(),
    input_guardrails=input_guardrails,
    output_guardrails=output_guardrails,
    tool_use_behavior="run_llm_again",
    reset_tool_choice=True,
    model=OpenAIChatCompletionsModel(
        model=f"{_cfg.model}-thinking",
        openai_client=AsyncOpenAI(),
        agent_name="Selection Agent",
        agent_type="selection_agent",
    ),
)


def transfer_to_selection_agent(**kwargs):  # pylint: disable=W0613
    """Hand back to the selection / routing agent."""
    return selection_agent
