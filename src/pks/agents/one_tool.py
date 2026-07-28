"""
CTF Agent with one tool
"""

from pks.sdk.agents import Agent, OpenAIChatCompletionsModel
from pks.tools.reconnaissance.generic_linux_command import generic_linux_command  # noqa
from pks.tools.misc.blackboard_tools import note_finding, set_flag  # noqa
from openai import AsyncOpenAI
from pks.util import create_system_prompt_renderer, load_prompt_template
from pks.config import get_config
from pks.agents.guardrails import get_security_guardrails

_cfg = get_config()
model_name = _cfg.model

# NOTE: This is needed when using LiteLLM Proxy Server
#
# # Create OpenAI client for the agent
# openai_client = AsyncOpenAI(
#     base_url = os.getenv('LITELLM_BASE_URL', 'http://localhost:4000'),
#     api_key=os.getenv('LITELLM_API_KEY', 'key')
# )

# # Check if we're using a Qwen model
# is_qwen = "qwen" in model_name.lower()

ctf_agent_system_prompt = load_prompt_template("prompts/system_ctf_agent.md")

# Loaded in openaichatcompletion client
api_key = _cfg.openai_api_key or "sk-placeholder-key-for-local-models"

# Get security guardrails for this high-risk agent
input_guardrails, output_guardrails = get_security_guardrails()

one_tool_agent = Agent(
    name="CTF agent",
    description="""Agent focused on conquering security challenges using generic linux commands
                   Expert in cybersecurity and exploitation.""",
    instructions=create_system_prompt_renderer(
        ctf_agent_system_prompt,
        cyber_micro_profile_key="ctf",
    ),
    tools=[
        generic_linux_command,
        note_finding,
        set_flag,
    ],
    input_guardrails=input_guardrails,
    output_guardrails=output_guardrails,
    model=OpenAIChatCompletionsModel(
        model=model_name,
        openai_client=AsyncOpenAI(api_key=api_key),
    ),
)


def transfer_to_one_tool_agent(**kwargs):  # pylint: disable=W0613
    """Transfer to ctf agent.
    Accepts any keyword arguments but ignores them."""
    return one_tool_agent
