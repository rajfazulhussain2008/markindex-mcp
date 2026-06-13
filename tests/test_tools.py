import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile

from markindex.config import settings
from markindex.server import documents
from markindex.tools.ingest import ingest_document, ingest_text
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

    def test_local_file_unsupported_extension(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("markindex.tools.ingest.settings.RAW_DIR", temp_dir):
                bad_ext_file = os.path.join(temp_dir, "bad.exe")
                with open(bad_ext_file, "w") as f:
                    f.write("test")
                res = ingest_document(bad_ext_file)
                self.assertFalse(res["success"])
                self.assertEqual(res["code"], "UNSUPPORTED_EXTENSION")

    @patch("markindex.tools.ingest.settings.MAX_TEXT_CHARS", 10)
    def test_ingest_text_too_large(self):
        res = ingest_text("Test", "This text is way too large for the 10 char limit")
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "TEXT_TOO_LARGE")

    def test_search_all_documents(self):
        from markindex.tools.query import search_all_documents

        documents.clear()

        # Ingest two documents
        ingest_text("Doc1", "# Vehicle Policy\nWe cover cars.")
        ingest_text("Doc2", "# Health Policy\nWe cover health. We also cover cars somewhat.")

        res = search_all_documents("cars", limit=10)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["data"]), 2)

        # Verify result contains global search keys
        first_result = res["data"][0]
        self.assertIn("document_id", first_result)
        self.assertIn("filename", first_result)
        self.assertIn("path", first_result)

        # Limit test
        res_limit = search_all_documents("cover", limit=1)
        self.assertTrue(res_limit["success"])
        self.assertEqual(len(res_limit["data"]), 1)

    def test_search_all_documents_validation(self):
        from markindex.tools.query import search_all_documents

        res = search_all_documents("   ")
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "EMPTY_QUERY")

        res_limit = search_all_documents("cars", limit=0)
        self.assertFalse(res_limit["success"])
        self.assertEqual(res_limit["code"], "INVALID_LIMIT")

    def test_search_sections_validation(self):
        from markindex.tools.query import search_sections

        res_ingest = ingest_text("SearchDoc", "# Car\nCars are good.")
        doc_id = res_ingest["data"]["document_id"]

        res = search_sections(doc_id, "")
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "EMPTY_QUERY")

        res_limit = search_sections(doc_id, "Car", limit=-5)
        self.assertFalse(res_limit["success"])
        self.assertEqual(res_limit["code"], "INVALID_LIMIT")

    def test_ingest_directory(self):
        from markindex.tools.ingest import ingest_directory

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("markindex.tools.ingest.settings.RAW_DIR", temp_dir):
                file1 = os.path.join(temp_dir, "file1.md")
                file2 = os.path.join(temp_dir, "file2.txt")
                with open(file1, "w") as f:
                    f.write("# Test1")
                with open(file2, "w") as f:
                    f.write("Test2")

                res = ingest_directory(temp_dir)
                self.assertTrue(res["success"])
                self.assertEqual(len(res["data"]["ingested"]), 2)

    def test_ingest_directory_external_denied(self):
        from markindex.tools.ingest import ingest_directory

        with tempfile.TemporaryDirectory() as temp_dir:
            res = ingest_directory(temp_dir)
            self.assertFalse(res["success"])
            self.assertEqual(res["code"], "ACCESS_DENIED")

    @patch("markindex.tools.ingest.ingest_document")
    def test_ingest_directory_partial_failure(self, mock_ingest):
        from markindex.tools.ingest import ingest_directory

        # return one success, one failure
        mock_ingest.side_effect = [
            {"success": True, "data": {"document_id": "1", "filename": "1.md", "size_chars": 10}},
            {"success": False, "error": "Failed to parse", "code": "INGESTION_ERROR"},
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("markindex.tools.ingest.settings.RAW_DIR", temp_dir):
                with open(os.path.join(temp_dir, "1.md"), "w") as f:
                    f.write("1")
                with open(os.path.join(temp_dir, "2.md"), "w") as f:
                    f.write("2")
                res = ingest_directory(temp_dir)
                self.assertTrue(res["success"])
                self.assertEqual(len(res["data"]["ingested"]), 1)
                self.assertEqual(len(res["data"]["failed"]), 1)

    @patch("youtube_transcript_api.YouTubeTranscriptApi.get_transcript")
    def test_ingest_youtube_valid(self, mock_get):
        from markindex.tools.ingest import ingest_youtube
        mock_get.return_value = [{"text": "Hello", "start": 0.0, "duration": 1.0}]
        res = ingest_youtube("dQw4w9WgXcQ")
        self.assertTrue(res["success"])
        self.assertIn("document_id", res["data"])

    def test_ingest_youtube_invalid_id(self):
        from markindex.tools.ingest import ingest_youtube
        res = ingest_youtube("invalid id space")
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "INVALID_YOUTUBE_ID")

    @patch("youtube_transcript_api.YouTubeTranscriptApi.get_transcript")
    def test_ingest_youtube_error(self, mock_get):
        from markindex.tools.ingest import ingest_youtube
        mock_get.side_effect = Exception("API failure")
        res = ingest_youtube("dQw4w9WgXcQ")
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "YOUTUBE_ERROR")

    @patch("markindex.tools.ingest.urllib.request.urlopen")
    def test_download_url_stream_size_limit(self, mock_urlopen):
        from markindex.tools.ingest import _download_url

        mock_response = MagicMock()
        def mock_get(key, default=None):
            if key == "Content-Length":
                return None
            return "text/html"
        mock_response.headers.get.side_effect = mock_get

        # generate huge data
        def read_chunk(*args):
            return b"x" * (1024 * 1024 * 10)  # 10MB chunks

        mock_response.read.side_effect = read_chunk
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with patch("markindex.tools.ingest.settings.MAX_FILE_MB", 1):
            with self.assertRaisesRegex(ValueError, "Download exceeded"):
                _download_url("http://example.com/huge")

    def test_get_adjacent_sections(self):
        from markindex.tools.navigate import get_adjacent_sections

        res_ingest = ingest_text("Nav", "# Sec1\n\n# Sec2\n\n# Sec3")
        doc_id = res_ingest["data"]["document_id"]

        res = get_adjacent_sections(doc_id, "Sec2")
        self.assertTrue(res["success"])
        self.assertIn("Sec1", res["data"]["previous"]["title"])
        self.assertIn("Sec3", res["data"]["next"]["title"])

    def test_get_document_outline(self):
        from markindex.tools.query import get_document_outline

        res_ingest = ingest_text("Out", "# H1\n## H2")
        doc_id = res_ingest["data"]["document_id"]
        res = get_document_outline(doc_id)
        self.assertTrue(res["success"])
        self.assertEqual(res["data"][0]["title"], "H1")

    def test_summarize_section(self):
        from markindex.tools.navigate import summarize_section

        long_text = (
            "A very long sentence about testing things out to make sure summarization "
            "works properly and returns exactly what we want without failing. " * 50
        )
        res_ingest = ingest_text("Sum", "# Long Sec\n\n" + long_text)
        doc_id = res_ingest["data"]["document_id"]
        res = summarize_section(doc_id, "Long Sec", num_sentences=1)
        self.assertTrue(res["success"])
        self.assertIn("summary", res["data"])

    def test_read_section_not_found_message(self):
        from markindex.tools.query import read_section

        res_ingest = ingest_text("Msg", "# Apple\n# Banana\n")
        doc_id = res_ingest["data"]["document_id"]
        res = read_section(doc_id, "Orange")
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "SECTION_NOT_FOUND")
        self.assertIn("Banana", res["error"])

    def test_delete_document(self):
        from markindex.tools.manage import delete_document

        res_ingest = ingest_text("DeleteMe", "Test")
        doc_id = res_ingest["data"]["document_id"]
        res = delete_document(doc_id)
        self.assertTrue(res["success"])
        self.assertNotIn(doc_id, documents)

    def test_delete_document_error(self):
        from markindex.tools.manage import delete_document
        res = delete_document("not-a-doc")
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "DOC_NOT_FOUND")

    def test_save_to_outputs_path_traversal(self):
        from markindex.tools.manage import save_to_outputs
        res = save_to_outputs("../outside.md", "content")
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "PATH_TRAVERSAL")

    def test_get_server_status(self):
        from markindex.tools.manage import get_server_status

        res = get_server_status()
        self.assertTrue(res["success"])
        self.assertIn("version", res["data"])
        self.assertIn("documents_indexed", res["data"])
        self.assertIn("status", res["data"])

    def test_get_adjacent_sections_errors(self):
        from markindex.tools.navigate import get_adjacent_sections

        res = get_adjacent_sections("not-a-doc", "Sec")
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "DOC_NOT_FOUND")

        res_ingest = ingest_text("NavErr", "# Sec1")
        doc_id = res_ingest["data"]["document_id"]
        res = get_adjacent_sections(doc_id, "Missing")
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "SECTION_NOT_FOUND")

    def test_summarize_section_errors(self):
        from markindex.tools.navigate import summarize_section

        res = summarize_section("not-a-doc", "Sec")
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "DOC_NOT_FOUND")

        res_ingest = ingest_text("SumErr", "# Sec1\n\n# EmptyParent\n## Child")
        doc_id = res_ingest["data"]["document_id"]

        res_missing = summarize_section(doc_id, "Missing")
        self.assertFalse(res_missing["success"])
        self.assertEqual(res_missing["code"], "SECTION_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
