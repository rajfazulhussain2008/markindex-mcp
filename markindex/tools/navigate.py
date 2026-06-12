"""Section navigation tools for MarkIndex MCP.

Provides tools for traversing the document tree using sibling and
parent navigation, and generating extractive section summaries.
"""

import json

from markindex.core.parser import find_section, get_flat_navigation_map
from markindex.core.summarizer import summarize_text
from markindex.exceptions import DocumentNotFoundError, SectionNotFoundError
from markindex.logger import get_logger
from markindex.server import mcp, documents

logger = get_logger(__name__)


def _require_document(doc_id: str) -> dict:
    if doc_id not in documents:
        raise DocumentNotFoundError(doc_id)
    return documents[doc_id]


@mcp.tool()
def get_adjacent_sections(doc_id: str, section_title: str) -> str:
    """Retrieve navigation context for a section.

    Returns the parent, previous, and next sections relative to
    the specified section.

    Args:
        doc_id: The document ID.
        section_title: Title of the section to navigate from.

    Returns:
        JSON object with parent, previous, and next section titles.
    """
    try:
        doc = _require_document(doc_id)
    except DocumentNotFoundError as exc:
        return str(exc)

    tree = doc["tree"]
    section_node = find_section(tree, section_title)
    if not section_node:
        return f"Error: Section '{section_title}' not found."

    nav_map = get_flat_navigation_map(tree)
    resolved = section_node["title"]

    if resolved not in nav_map:
        return f"Error: Navigation mapping failed for '{resolved}'."

    return json.dumps(nav_map[resolved], indent=2)


@mcp.tool()
def summarize_section(doc_id: str, section_title: str, num_sentences: int = 5) -> str:
    """Generate an extractive summary of a document section.

    Uses term-frequency scoring to select the most informative sentences.

    Args:
        doc_id: The document ID.
        section_title: Title of the section to summarize.
        num_sentences: Number of sentences to extract.

    Returns:
        Markdown-formatted summary.
    """
    try:
        doc = _require_document(doc_id)
    except DocumentNotFoundError as exc:
        return str(exc)

    tree = doc["tree"]
    section_node = find_section(tree, section_title)
    if not section_node:
        return f"Error: Section '{section_title}' not found."

    content = section_node["content"]
    if not content.strip():
        return f"Section '{section_node['title']}' has no direct content. It only contains sub-sections."

    summary = summarize_text(content, num_sentences)
    return f"### Summary of: {section_node['title']}\n\n{summary}"
