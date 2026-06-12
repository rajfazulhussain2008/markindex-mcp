import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from markindex.server import documents
from markindex.tools.ingest import ingest_text


class TestStartup(unittest.TestCase):
    def test_server_startup(self):
        try:
            subprocess.run(
                [sys.executable, "-m", "markindex"], timeout=2, capture_output=True, check=True
            )
        except subprocess.TimeoutExpired:
            pass  # Expected, stdio server waits for input
        except subprocess.CalledProcessError as e:
            self.fail(f"Server startup failed: {e.stderr.decode()}")

    def test_register_tools(self):
        try:
            from markindex.server import _register_tools

            _register_tools()
        except Exception as e:
            self.fail(f"_register_tools raised an exception: {e}")


class TestCache(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.patcher = patch("markindex.core.storage.settings.WIKI_DIR", self.temp_dir.name)
        self.patcher.start()
        documents.clear()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()
        documents.clear()

    def test_cache_reload(self):
        from markindex.server import _load_cache
        from markindex.tools.manage import list_documents
        from markindex.tools.query import search_sections, read_section

        res = ingest_text("CacheTest", "# Header\nContent")
        self.assertTrue(res["success"])
        doc_id = res["data"]["document_id"]
        
        # clear memory
        documents.clear()
        
        # reload
        _load_cache()
        
        self.assertIn(doc_id, documents)
        self.assertEqual(documents[doc_id]["metadata"]["filename"], "CacheTest")
        self.assertIn("Header", documents[doc_id]["markdown"])
        
        # verify tools work on loaded cache
        res_list = list_documents()
        self.assertEqual(len(res_list["data"]), 1)
        
        res_search = search_sections(doc_id, "Content")
        self.assertTrue(res_search["success"])
        self.assertEqual(len(res_search["data"]), 1)
        
        res_read = read_section(doc_id, "header")
        self.assertTrue(res_read["success"])
        self.assertIn("Content", res_read["data"])


if __name__ == "__main__":
    unittest.main()
