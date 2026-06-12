import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markindex.core.parser import (
    find_section,
    get_flat_navigation_map,
    get_outline,
    parse_markdown_to_tree,
    section_to_markdown,
)
from markindex.core.search import rank_sections_tfidf
from markindex.core.storage import parse_frontmatter, serialize_frontmatter
from markindex.core.summarizer import summarize_text

SAMPLE_MARKDOWN = """# Introduction

This is the introduction to the document.

## Background

Some background information here about the project.

## Objectives

The objectives of this project are:
- Build a scalable system
- Ensure reliability

# Methodology

We used the following methodology.

## Data Collection

Data was collected from multiple sources including surveys and databases.

## Analysis

Statistical analysis was performed on the collected data.

# Results

The results are presented below.

## Key Findings

The key findings indicate significant improvement in performance.

## Discussion

We discuss the implications of these findings in detail.

# Conclusion

In conclusion, the project was successful and met all objectives.
"""


class TestParser(unittest.TestCase):
    def setUp(self):
        self.tree = parse_markdown_to_tree(SAMPLE_MARKDOWN)

    def test_top_level_sections(self):
        titles = [n["title"] for n in self.tree]
        self.assertEqual(titles, ["Introduction", "Methodology", "Results", "Conclusion"])

    def test_children_count(self):
        intro = self.tree[0]
        self.assertEqual(len(intro["children"]), 2)
        self.assertEqual(intro["children"][0]["title"], "Background")
        self.assertEqual(intro["children"][1]["title"], "Objectives")

    def test_duplicate_section_ids(self):
        markdown = "# Chapter 1\n## Summary\nfirst\n## Summary\nsecond\n"
        tree = parse_markdown_to_tree(markdown)
        ch1 = tree[0]
        s1 = ch1["children"][0]
        s2 = ch1["children"][1]

        self.assertEqual(s1["id"], "chapter-1-summary")
        self.assertEqual(s2["id"], "chapter-1-summary-2")
        self.assertEqual(s2["path"], "Chapter 1 > Summary (2)")

    def test_section_content(self):
        conclusion = self.tree[3]
        self.assertIn("successful", conclusion["content"])

    def test_section_to_markdown(self):
        md = section_to_markdown(self.tree[0])
        self.assertIn("# Introduction", md)
        self.assertIn("## Background", md)

    def test_outline_structure(self):
        outline = get_outline(self.tree)
        self.assertEqual(len(outline), 4)
        self.assertIn("size_chars", outline[0])
        self.assertIn("children", outline[0])


class TestSectionFinder(unittest.TestCase):
    def setUp(self):
        self.tree = parse_markdown_to_tree(SAMPLE_MARKDOWN)

    def test_exact_match(self):
        node = find_section(self.tree, "Background")
        self.assertIsNotNone(node)
        self.assertEqual(node["title"], "Background")

    def test_case_insensitive(self):
        node = find_section(self.tree, "background")
        self.assertIsNotNone(node)
        self.assertEqual(node["title"], "Background")

    def test_substring_match(self):
        node = find_section(self.tree, "Key Find")
        self.assertIsNotNone(node)
        self.assertEqual(node["title"], "Key Findings")

    def test_fuzzy_match(self):
        node = find_section(self.tree, "Introducton")  # Typo
        self.assertIsNotNone(node)
        self.assertEqual(node["title"], "Introduction")

    def test_not_found(self):
        node = find_section(self.tree, "zzzzzzzzzzzzz")
        self.assertIsNone(node)


class TestNavigation(unittest.TestCase):
    def setUp(self):
        self.tree = parse_markdown_to_tree(SAMPLE_MARKDOWN)
        self.nav = get_flat_navigation_map(self.tree)

    def test_nav_map_keys(self):
        self.assertIn("introduction", self.nav)
        self.assertIn("introduction-background", self.nav)
        self.assertIn("conclusion", self.nav)

    def test_sibling_links(self):
        bg = self.nav["introduction-background"]
        self.assertEqual(bg["parent"]["title"], "Introduction")
        self.assertEqual(bg["previous"]["id"], "introduction")
        self.assertEqual(bg["next"]["id"], "introduction-objectives")

    def test_first_section_has_no_previous(self):
        intro = self.nav["introduction"]
        self.assertIsNone(intro["previous"])

    def test_last_section_has_no_next(self):
        conclusion = self.nav["conclusion"]
        self.assertIsNone(conclusion["next"])


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.tree = parse_markdown_to_tree(SAMPLE_MARKDOWN)

    def test_basic_search(self):
        results = rank_sections_tfidf(self.tree, "methodology")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["section_title"], "Methodology")

    def test_snippets_generated(self):
        results = rank_sections_tfidf(self.tree, "performance")
        self.assertGreater(len(results), 0)
        self.assertGreater(len(results[0]["snippets"]), 0)

    def test_snippets_fallback_and_deduplication(self):
        results = rank_sections_tfidf(self.tree, "vehicle performance")
        self.assertGreater(len(results), 0)
        snippets = results[0]["snippets"]
        self.assertGreater(len(snippets), 0)
        self.assertEqual(len(snippets), len(set(snippets)))

    def test_title_boost(self):
        results = rank_sections_tfidf(self.tree, "results")
        top = results[0]
        self.assertTrue(top["title_matched"])
        self.assertGreater(top["score"], 4.0)

    def test_exact_phrase_boost(self):
        results = rank_sections_tfidf(self.tree, "significant improvement in performance")
        top = results[0]
        self.assertEqual(top["section_title"], "Key Findings")
        self.assertGreater(top["score"], 5.0)

    def test_no_results(self):
        results = rank_sections_tfidf(self.tree, "xyznonexistent123")
        self.assertEqual(len(results), 0)

    def test_regex_search(self):
        results = rank_sections_tfidf(self.tree, r"collect\w+", is_regex=True)
        self.assertGreater(len(results), 0)


class TestSummarizer(unittest.TestCase):
    def test_short_text_unchanged(self):
        text = "Short sentence one. Short sentence two."
        result = summarize_text(text, num_sentences=5)
        self.assertEqual(result, text)

    def test_summarizes_long_text(self):
        text = ". ".join([f"Sentence number {i} about topic" for i in range(20)]) + "."
        result = summarize_text(text, num_sentences=3)
        self.assertLess(len(result), len(text))


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.patcher = patch("markindex.core.storage.settings.WIKI_DIR", self.temp_dir.name)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_round_trip(self):
        metadata = {
            "filepath": "/test/doc.pdf",
            "filename": "doc.pdf",
            "ingested_at": "2026-01-01T00:00:00",
            "size_chars": 1234,
        }
        content = "# Hello World\n\nSome content here."
        serialized = serialize_frontmatter(metadata, content)
        parsed_meta, parsed_content = parse_frontmatter(serialized)

        self.assertEqual(parsed_meta["filepath"], "/test/doc.pdf")
        self.assertEqual(parsed_meta["filename"], "doc.pdf")
        self.assertEqual(parsed_meta["size_chars"], 1234)
        self.assertIn("Hello World", parsed_content)

    def test_no_frontmatter(self):
        content = "# Just Markdown\n\nNo frontmatter here."
        meta, md = parse_frontmatter(content)
        self.assertEqual(meta, {})
        self.assertEqual(md, content)


if __name__ == "__main__":
    unittest.main()
