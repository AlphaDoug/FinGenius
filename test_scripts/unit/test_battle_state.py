import os
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.environment.battle import BattleState



class TestBattleState(unittest.TestCase):
    def test_record_vote_and_results(self):
        state = BattleState(active_agents={"a": "A", "b": "B"})
        state.record_vote("a", "invalid", 1)
        self.assertEqual(sum(state.vote_results.values()), 0)

        state.record_vote("a", "bullish", 1)
        self.assertEqual(state.final_votes["a"], "bullish")
        self.assertEqual(state.vote_results["bullish"], 1)

    def test_add_highlight_dedup_and_limit(self):
        state = BattleState()
        content = "这个观点非常重要，需要高亮显示。"

        state.add_highlight("AgentA", content)
        state.add_highlight("AgentA", content)
        self.assertEqual(len(state.battle_highlights), 1)

        state.add_highlight("AgentA", content + "1")
        state.add_highlight("AgentA", content + "2")
        state.add_highlight("AgentA", content + "3")
        self.assertEqual(len(state.battle_highlights), 3)
