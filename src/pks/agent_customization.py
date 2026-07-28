import os
from pks.sdk.agents import Agent, OpenAIChatCompletionsModel
from pks.tools.reconnaissance.generic_linux_command import generic_linux_command  # noqa
from openai import AsyncOpenAI
from pks.util import create_system_prompt_renderer
from pks.agents.guardrails import get_security_guardrails

instructions = """Behave as a pentester and 
                 use the generic_linux_command tool 
                 to run simulated Linux commands. 
                 Stay focused, concise, and task-oriented"""

custom_agent = Agent(
    name="Custom agent",
    description="Offensive security pentesting agent.",
    instructions=create_system_prompt_renderer(
        instructions,
        cyber_micro_profile_key="redteam",
    ),
    tools=[
        generic_linux_command,
    ],
    model=OpenAIChatCompletionsModel(
        model=os.getenv("PKS_MODEL", "alias1"),
        openai_client=AsyncOpenAI(),
    ),
)
