import os
import sys
import unittest
from unittest.mock import AsyncMock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.tool.base import BaseTool, ToolResult, ToolFailure
from src.tool.tool_collection import ToolCollection
from src.tool.mcp_client import MCPClientTool
from src.tool.battle import Battle



class DummyTool(BaseTool):
    name: str = "dummy"
    description: str = "dummy tool"

    async def execute(self, **kwargs):
        return ToolResult(output="ok")


class TestTools(unittest.IsolatedAsyncioTestCase):
    async def test_tool_collection_execute(self):
        tools = ToolCollection(DummyTool())
        result_ok = await tools.execute(name="dummy", tool_input={})
        self.assertEqual(result_ok.output, "ok")

        result_bad = await tools.execute(name="missing", tool_input={})
        self.assertIsInstance(result_bad, ToolFailure)

    async def test_mcp_client_tool_no_session(self):
        tool = MCPClientTool(name="mcp_demo", description="demo")
        result = await tool.execute()
        self.assertIsNotNone(result.error)

    async def test_battle_tool_controller(self):
        tool = Battle(agent_id="agent1")
        result = await tool.execute(speak="hello", vote="bullish")
        self.assertIsNotNone(result.error)

        controller = AsyncMock()
        controller.handle_speak = AsyncMock(return_value=ToolResult(output="ok"))
        controller.handle_vote = AsyncMock(return_value=ToolResult(output="ok"))

        tool.controller = controller
        result2 = await tool.execute(speak="hello", vote="bullish")
        self.assertIsNone(result2.error)
        self.assertIn("agent1", result2.output)
