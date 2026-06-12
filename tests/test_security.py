import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestManageSecurity(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.patcher = patch("markindex.tools.manage.settings.OUTPUTS_DIR", self.temp_dir.name)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_save_to_outputs_path_traversal(self):
        from markindex.tools.manage import save_to_outputs
        res = save_to_outputs("../../../windows/system32/hack.md", "hacked")
        self.assertFalse(res["success"])
        self.assertIn("path traversal", res["error"])

    def test_save_to_outputs_valid(self):
        from markindex.tools.manage import save_to_outputs
        res = save_to_outputs("valid_report.md", "content")
        self.assertTrue(res["success"])
        self.assertIn("valid_report.md", res["data"]["saved_path"])

if __name__ == "__main__":
    unittest.main()
