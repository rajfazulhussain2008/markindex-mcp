"""Section navigation tools for MarkIndex MCP.

Provides tools for traversing the document tree using sibling and
parent navigation, reading sections, and generating extractive summaries.
"""

from typing import Any

from markindex.core.parser import find_section, get_flat_navigation_map, section_to_markdown
from markindex.core.summarizer import summarize_text
from markindex.exceptions import DocumentNotFoundError
from markindex.logger import get_logger
from markindex.server import mcp, documents

logger = get_logger(__name__)


def _require_document(doc_id: str) -> dict:
    if doc_id not in documents:
        raise DocumentNotFoundError(doc_id)
    return documents[doc_id]


@mcp.tool()
def get_adjacent_sections(doc_id: str, section_title: str) -> dict[str, Any]:
    """Retrieve navigation context for a section.

    Returns the parent, previous, and next sections relative to
    the specified section.

    Args:
        doc_id: The document ID.
        section_title: Title or ID of the section to navigate from.

    Returns:
        Dict with status and data containing navigation context.
    """
    try:
        doc = _require_document(doc_id)
    except DocumentNotFoundError as exc:
        return {"success": False, "data": None, "error": str(exc), "code": "DOC_NOT_FOUND"}

    tree = doc["tree"]
    section_node = find_section(tree, section_title)
    if not section_node:
        return {"success": False, "data": None, "error": f"Section '{section_title}' not found.", "code": "SECTION_NOT_FOUND"}

    nav_map = get_flat_navigation_map(tree)
    node_id = section_node["id"]

    if node_id not in nav_map:
        return {"success": False, "data": None, "error": f"Navigation mapping failed for '{node_id}'.", "code": "MAP_FAILED"}

    return {"success": True, "data": nav_map[node_id], "error": None, "code": None}


@mcp.tool()
def summarize_section(doc_id: str, section_title: str, num_sentences: int = 5) -> dict[str, Any]:
    """Generate an extractive summary of a document section.

    Uses term-frequency scoring to select the most informative sentences.

    Args:
        doc_id: The document ID.
        section_title: Title or ID of the section to summarize.
        num_sentences: Number of sentences to extract.

    Returns:
        Dict with status and markdown-formatted summary.
    """
    try:
        doc = _require_document(doc_id)
    except DocumentNotFoundError as exc:
        return {"success": False, "data": None, "error": str(exc), "code": "DOC_NOT_FOUND"}

    tree = doc["tree"]
    section_node = find_section(tree, section_title)
    if not section_node:
        return {"success": False, "data": None, "error": f"Section '{section_title}' not found.", "code": "SECTION_NOT_FOUND"}

    content = section_node["content"]
    if not content.strip():
        return {"success": False, "data": None, "error": f"Section '{section_node['title']}' has no direct content. It only contains sub-sections.", "code": "NO_CONTENT"}

    summary = summarize_text(content, num_sentences)
    return {"success": True, "data": f"### Summary of: {section_node['title']}\n\n{summary}", "error": None, "code": None}
