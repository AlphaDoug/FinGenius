import os
import sys
import unittest
from unittest.mock import AsyncMock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.environment.battle import BattleEnvironment



class TestBattleEnvironment(unittest.IsolatedAsyncioTestCase):
    async def test_handle_vote_validation(self):
        env = BattleEnvironment()
        env.state.active_agents = {"agent1": "Agent1"}
        env.state.terminated_agents = {}
        env._broadcast_message = AsyncMock()

        result = await env.handle_vote("agent1", "invalid")
        self.assertIsNotNone(result.error)

        result_ok = await env.handle_vote("agent1", "bullish")
        self.assertIsNone(result_ok.error)
        self.assertEqual(env.state.final_votes["agent1"], "bullish")

    async def test_handle_speak_unregistered(self):
        env = BattleEnvironment()
        env._broadcast_message = AsyncMock()
        result = await env.handle_speak("ghost", "hello")
        self.assertIsNotNone(result.error)
