import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markindex.server import documents
from markindex.tools.ingest import ingest_text
from markindex.tools.manage import list_documents


class TestIngestionTools(unittest.TestCase):
    def setUp(self):
        documents.clear()

    def test_ingest_text_schema(self):
        res = ingest_text("Test Doc", "# Hello\nworld")
        self.assertTrue(res["success"])
        self.assertIn("document_id", res["data"])
        
        docs = list_documents()
        self.assertTrue(docs["success"])
        self.assertEqual(len(docs["data"]), 1)
        self.assertEqual(docs["data"][0]["filename"], "Test Doc")
        self.assertEqual(docs["data"][0]["size_chars"], 13)

    @patch("markindex.tools.ingest.urllib.request.urlopen")
    def test_download_url_valid(self, mock_urlopen):
        from markindex.tools.ingest import _download_url
        
        mock_response = MagicMock()
        mock_response.headers.get.side_effect = lambda key, default="": "text/html" if key == "Content-Type" else default
        mock_response.read.side_effect = [b"hello web", b""]
        mock_urlopen.return_value.__enter__.return_value = mock_response

        temp_path, _ = _download_url("http://example.com/page.html")
        self.assertTrue(os.path.exists(temp_path))
        self.assertTrue(temp_path.endswith(".html"))
        
        with open(temp_path, "rb") as f:
            self.assertEqual(f.read(), b"hello web")
        os.remove(temp_path)

if __name__ == "__main__":
    unittest.main()
