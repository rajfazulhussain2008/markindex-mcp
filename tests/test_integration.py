"""Integration tests for MarkIndex MCP.

Tests the core parsing, search, summarization, and storage modules
to ensure end-to-end correctness of the Page Index RAG pipeline.
"""

import json
import os
import sys
import unittest

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markindex.core.parser import (
    find_section,
    get_flat_navigation_map,
    get_outline,
    parse_markdown_to_tree,
    section_to_markdown,
)
from markindex.core.search import rank_sections_tfidf
from markindex.core.summarizer import summarize_text
from markindex.core.storage import parse_frontmatter, serialize_frontmatter


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
    """Test the hierarchical document parser."""

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
    """Test multi-phase section title resolution."""

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
    """Test flat navigation map generation."""

    def setUp(self):
        self.tree = parse_markdown_to_tree(SAMPLE_MARKDOWN)
        self.nav = get_flat_navigation_map(self.tree)

    def test_nav_map_keys(self):
        self.assertIn("Introduction", self.nav)
        self.assertIn("Introduction > Background", self.nav)
        self.assertIn("Conclusion", self.nav)

    def test_sibling_links(self):
        bg = self.nav["Introduction > Background"]
        self.assertEqual(bg["parent"], "Introduction")
        self.assertEqual(bg["previous"], "Introduction")
        self.assertEqual(bg["next"], "Introduction > Objectives")

    def test_first_section_has_no_previous(self):
        intro = self.nav["Introduction"]
        self.assertIsNone(intro["previous"])

    def test_last_section_has_no_next(self):
        conclusion = self.nav["Conclusion"]
        self.assertIsNone(conclusion["next"])


class TestSearch(unittest.TestCase):
    """Test TF-IDF ranked search engine."""

    def setUp(self):
        self.tree = parse_markdown_to_tree(SAMPLE_MARKDOWN)

    def test_basic_search(self):
        results = rank_sections_tfidf(self.tree, "methodology")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["section_title"], "Methodology")

    def test_title_boost(self):
        results = rank_sections_tfidf(self.tree, "results")
        top = results[0]
        self.assertTrue(top["title_matched"])
        self.assertGreater(top["score"], 5.0)

    def test_exact_phrase_boost(self):
        results = rank_sections_tfidf(self.tree, "significant improvement in performance")
        top = results[0]
        self.assertEqual(top["section_title"], "Key Findings")
        self.assertGreater(top["score"], 15.0)

    def test_no_results(self):
        results = rank_sections_tfidf(self.tree, "xyznonexistent123")
        self.assertEqual(len(results), 0)

    def test_regex_search(self):
        results = rank_sections_tfidf(self.tree, r"collect\w+", is_regex=True)
        self.assertGreater(len(results), 0)

    def test_snippets_generated(self):
        results = rank_sections_tfidf(self.tree, "performance")
        matched = [r for r in results if r["snippets"]]
        self.assertGreater(len(matched), 0)


class TestSummarizer(unittest.TestCase):
    """Test extractive summarization."""

    def test_short_text_unchanged(self):
        text = "Short sentence one. Short sentence two."
        result = summarize_text(text, num_sentences=5)
        self.assertEqual(result, text)

    def test_summarizes_long_text(self):
        text = ". ".join([f"Sentence number {i} about topic" for i in range(20)]) + "."
        result = summarize_text(text, num_sentences=3)
        # Should be shorter than original
        self.assertLess(len(result), len(text))


class TestStorage(unittest.TestCase):
    """Test frontmatter serialization and parsing."""

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


class TestManageSecurity(unittest.TestCase):
    """Test security constraints in management tools."""

    def test_save_to_outputs_path_traversal(self):
        from markindex.tools.manage import save_to_outputs
        res = save_to_outputs("../../../windows/system32/hack.md", "hacked")
        self.assertIn("Error: Invalid filename path traversal detected", res)

    def test_save_to_outputs_valid(self):
        from markindex.tools.manage import save_to_outputs
        res = save_to_outputs("valid_report.md", "content")
        self.assertIn("Successfully saved", res)


if __name__ == "__main__":
    unittest.main(verbosity=2)
