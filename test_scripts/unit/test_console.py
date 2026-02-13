import os
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.console import FinGeniusVisualizer



class TestConsoleVisualizer(unittest.TestCase):
    def test_tool_call_and_progress_stats(self):
        visualizer = FinGeniusVisualizer()
        self.assertEqual(visualizer.progress_stats["tool_calls"], 0)
        self.assertEqual(visualizer.progress_stats["llm_calls"], 0)

        visualizer.show_tool_call("demo_tool", {"a": 1}, agent_name="System")
        self.assertEqual(visualizer.progress_stats["tool_calls"], 1)

        visualizer.show_progress_update("阶段1")
        self.assertEqual(visualizer.progress_stats["llm_calls"], 1)
