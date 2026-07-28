from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from pks.sdk.agents import Agent
from pks.tools.vision import view_image


@pytest.mark.asyncio
async def test_view_image_selects_valid_local_pixels(tmp_path: Path) -> None:
    image_path = tmp_path / "chart.png"
    Image.new("RGB", (12, 8), "white").save(image_path, "PNG")

    result = await view_image.on_invoke_tool(
        SimpleNamespace(),
        json.dumps({"paths": [str(image_path)]}),
    )

    assert "[PKS view_image selection]" in result
    assert f"{image_path.resolve()}: PNG image data, 12 x 8" in result


@pytest.mark.asyncio
async def test_view_image_is_available_to_every_agent_once() -> None:
    agent = Agent(name="test")

    first = await agent.get_all_tools()
    second = await agent.get_all_tools()

    assert [tool.name for tool in first].count("view_image") == 1
    assert [tool.name for tool in second].count("view_image") == 1
