import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.environment.research import ResearchEnvironment
from src.tool.stock_info_request import StockInfoResponse



class DummyMemory:
    def __init__(self):
        self.messages = []

    def add_message(self, message):
        self.messages.append(message)


class DummyAgent:
    def __init__(self, name: str):
        self.name = name
        self.memory = DummyMemory()

    async def run(self, stock_code: str):
        return f"result-{self.name}-{stock_code}"


class TestResearchEnvironment(unittest.IsolatedAsyncioTestCase):
    async def test_run_success(self):
        env = ResearchEnvironment(max_steps=1)
        env.agents = {
            "sentiment_agent": DummyAgent("sentiment_agent"),
            "risk_control_agent": DummyAgent("risk_control_agent"),
        }
        env.analysis_mapping = {
            "sentiment_agent": "sentiment",
            "risk_control_agent": "risk",
        }

        mock_response = StockInfoResponse(
            output={
                "current_trading_day": "2026-02-13",
                "basic_info": {"name": "Demo"},
            }
        )

        with patch("src.environment.research.StockInfoRequest.execute", new=AsyncMock(return_value=mock_response)), \
             patch("asyncio.sleep", new=AsyncMock()):
            result = await env.run("000001")

        self.assertEqual(result["sentiment"], "result-sentiment_agent-000001")
        self.assertEqual(result["risk"], "result-risk_control_agent-000001")
        self.assertIn("basic_info", result)
        self.assertEqual(result["stock_code"], "000001")

    async def test_run_no_agents(self):
        env = ResearchEnvironment()
        env.agents = {}
        env.analysis_mapping = {"sentiment_agent": "sentiment"}

        mock_response = StockInfoResponse(output={"current_trading_day": "2026-02-13", "basic_info": {}})

        with patch("src.environment.research.StockInfoRequest.execute", new=AsyncMock(return_value=mock_response)), \
             patch("asyncio.sleep", new=AsyncMock()):
            result = await env.run("000001")

        self.assertIn("error", result)
