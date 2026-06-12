import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile

from markindex.config import settings
from markindex.server import documents
from markindex.tools.ingest import ingest_text, ingest_document
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
        
        def mock_header_get(key, default=""):
            return "text/html" if key == "Content-Type" else default

        mock_response.headers.get.side_effect = mock_header_get
        mock_response.read.side_effect = [b"hello web", b""]
        mock_urlopen.return_value.__enter__.return_value = mock_response

        temp_path, _ = _download_url("http://example.com/page.html")
        self.assertTrue(os.path.exists(temp_path))
        self.assertTrue(temp_path.endswith(".html"))
        
        with open(temp_path, "rb") as f:
            self.assertEqual(f.read(), b"hello web")
        os.remove(temp_path)

    def test_download_url_invalid_scheme(self):
        from markindex.tools.ingest import _download_url
        with self.assertRaisesRegex(ValueError, "Only http and https schemes are supported."):
            _download_url("ftp://example.com/file.pdf")

    @patch("markindex.tools.ingest.urllib.request.urlopen")
    def test_download_url_content_length_too_large(self, mock_urlopen):
        from markindex.tools.ingest import _download_url
        mock_response = MagicMock()
        def mock_header_get(key, default=""):
            if key == "Content-Length":
                return str(settings.MAX_FILE_MB * 1024 * 1024 + 1)
            return default
        mock_response.headers.get.side_effect = mock_header_get
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with self.assertRaisesRegex(ValueError, "File too large"):
            _download_url("http://example.com/file.pdf")

    @patch("markindex.tools.ingest.urllib.request.urlopen")
    def test_download_url_unsupported_content_type(self, mock_urlopen):
        from markindex.tools.ingest import _download_url
        mock_response = MagicMock()
        def mock_header_get(key, default=""):
            return "video/mp4" if key == "Content-Type" else default
        mock_response.headers.get.side_effect = mock_header_get
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with self.assertRaisesRegex(ValueError, "Unsupported content type: video/mp4"):
            _download_url("http://example.com/video.mp4")

    @patch("markindex.tools.ingest.urllib.request.urlopen")
    def test_download_url_query_suffix(self, mock_urlopen):
        from markindex.tools.ingest import _download_url
        mock_response = MagicMock()
        def mock_header_get(key, default=""):
            return "application/pdf" if key == "Content-Type" else default
        mock_response.headers.get.side_effect = mock_header_get
        mock_response.read.side_effect = [b"pdf data", b""]
        mock_urlopen.return_value.__enter__.return_value = mock_response

        temp_path, _ = _download_url("https://example.com/report.pdf?token=abc")
        self.assertTrue(temp_path.endswith(".pdf"))
        os.remove(temp_path)

    @patch("markindex.tools.ingest.urllib.request.urlopen")
    def test_download_url_fallback_suffix(self, mock_urlopen):
        from markindex.tools.ingest import _download_url
        mock_response = MagicMock()
        def mock_header_get(key, default=""):
            return "text/html" if key == "Content-Type" else default
        mock_response.headers.get.side_effect = mock_header_get
        mock_response.read.side_effect = [b"html data", b""]
        mock_urlopen.return_value.__enter__.return_value = mock_response

        temp_path, _ = _download_url("https://example.com/download")
        self.assertTrue(temp_path.endswith(".html"))
        os.remove(temp_path)

    @patch("markindex.tools.ingest.settings.MAX_FILE_MB", 0.0001)  # approx 100 bytes
    def test_local_file_size_limits(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Patch RAW_DIR so ingest_document thinks our temp_dir is RAW_DIR
            with patch("markindex.tools.ingest.settings.RAW_DIR", temp_dir):
                small_file = os.path.join(temp_dir, "small.txt")
                with open(small_file, "w") as f:
                    f.write("small")
                
                large_file = os.path.join(temp_dir, "large.txt")
                with open(large_file, "w") as f:
                    f.write("x" * 200)  # > 100 bytes
                
                # Should pass
                res1 = ingest_document(small_file)
                self.assertTrue(res1["success"])

                # Should fail with FILE_TOO_LARGE
                res2 = ingest_document(large_file)
                self.assertFalse(res2["success"])
                self.assertEqual(res2["code"], "FILE_TOO_LARGE")
                self.assertIn("File too large", res2["error"])

if __name__ == "__main__":
    unittest.main()
