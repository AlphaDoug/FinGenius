import os
import sys
import shutil
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.utils.report_manager import SimpleReportManager



class TestReportManager(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.join(REPO_ROOT, "test_data", "report_tests")
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)
        self.manager = SimpleReportManager(base_dir=self.base_dir)

    def tearDown(self):
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)

    def test_save_and_list_reports(self):
        ok_html = self.manager.save_html_report("000001", "<html>demo</html>")
        ok_debate = self.manager.save_debate_report("000001", {"a": 1})
        ok_vote = self.manager.save_vote_report("000001", {"bullish": 3, "bearish": 2})

        self.assertTrue(ok_html)
        self.assertTrue(ok_debate)
        self.assertTrue(ok_vote)

        reports = self.manager.list_reports(limit=10)
        self.assertGreaterEqual(len(reports), 3)

    def test_load_report(self):
        self.manager.save_html_report("000002", "<html>demo2</html>")
        reports = self.manager.list_reports(report_type="html", limit=1)
        report = self.manager.load_report("html", reports[0]["filename"])
        self.assertIsNotNone(report)
        self.assertIn("content", report)
