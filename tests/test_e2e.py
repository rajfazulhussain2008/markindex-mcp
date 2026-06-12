import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markindex.tools.ingest import ingest_text
from markindex.tools.manage import delete_document, list_documents
from markindex.tools.navigate import get_adjacent_sections
from markindex.tools.query import get_document_outline, read_section, search_sections


class TestEndToEndWorkflow(unittest.TestCase):
    def setUp(self):
        # We need a clean state for the e2e test.
        # We will patch WIKI_DIR so it doesn't touch real files.
        self.temp_dir = tempfile.TemporaryDirectory()
        self.patcher = patch("markindex.core.storage.settings.WIKI_DIR", self.temp_dir.name)
        self.patcher.start()
        from markindex.server import documents

        documents.clear()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_workflow(self):
        # 1. Ingest
        markdown = """# Alpha
This is alpha section.
## Bravo
This is bravo.
# Charlie
This is charlie.
"""
        res_ingest = ingest_text("E2E Test Document", markdown)
        self.assertTrue(res_ingest["success"])
        doc_id = res_ingest["data"]["document_id"]

        # 2. List
        res_list = list_documents()
        self.assertTrue(res_list["success"])
        self.assertEqual(len(res_list["data"]), 1)
        self.assertEqual(res_list["data"][0]["id"], doc_id)

        # 3. Outline
        res_outline = get_document_outline(doc_id)
        self.assertTrue(res_outline["success"])
        self.assertEqual(len(res_outline["data"]), 2)  # Alpha, Charlie

        # 4. Search
        res_search = search_sections(doc_id, "bravo")
        self.assertTrue(res_search["success"])
        self.assertGreater(len(res_search["data"]), 0)
        self.assertEqual(res_search["data"][0]["section_title"], "Bravo")

        # 5. Read
        res_read = read_section(doc_id, "Bravo")
        self.assertTrue(res_read["success"])
        self.assertIn("This is bravo.", res_read["data"])

        # 6. Navigate
        res_nav = get_adjacent_sections(doc_id, "Bravo")
        self.assertTrue(res_nav["success"])
        self.assertEqual(res_nav["data"]["parent"]["title"], "Alpha")
        self.assertEqual(res_nav["data"]["previous"]["title"], "Alpha")
        self.assertEqual(res_nav["data"]["next"]["title"], "Charlie")

        # 7. Delete
        res_delete = delete_document(doc_id)
        self.assertTrue(res_delete["success"])

        res_list2 = list_documents()
        self.assertTrue(res_list2["success"])
        self.assertEqual(len(res_list2["data"]), 0)


if __name__ == "__main__":
    unittest.main()
