"""Section navigation tools for MarkIndex MCP.

Provides tools for traversing the document tree using sibling and
parent navigation, reading sections, and generating extractive summaries.
"""

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
def get_adjacent_sections(doc_id: str, section_title: str) -> dict:
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
        return {"status": "error", "message": str(exc)}

    tree = doc["tree"]
    section_node = find_section(tree, section_title)
    if not section_node:
        return {"status": "error", "message": f"Section '{section_title}' not found."}

    nav_map = get_flat_navigation_map(tree)
    node_id = section_node["id"]

    if node_id not in nav_map:
        return {"status": "error", "message": f"Navigation mapping failed for '{node_id}'."}

    return {"status": "success", "data": nav_map[node_id]}


@mcp.tool()
def read_section(doc_id: str, section_title: str) -> dict:
    """Read the full content of a specific document section.

    Args:
        doc_id: The document ID.
        section_title: Title or ID of the section to read.

    Returns:
        Dict with status and markdown content.
    """
    try:
        doc = _require_document(doc_id)
    except DocumentNotFoundError as exc:
        return {"status": "error", "message": str(exc)}

    section_node = find_section(doc["tree"], section_title)
    if not section_node:
        return {"status": "error", "message": f"Section '{section_title}' not found."}

    return {"status": "success", "data": section_to_markdown(section_node)}


@mcp.tool()
def summarize_section(doc_id: str, section_title: str, num_sentences: int = 5) -> dict:
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
        return {"status": "error", "message": str(exc)}

    tree = doc["tree"]
    section_node = find_section(tree, section_title)
    if not section_node:
        return {"status": "error", "message": f"Section '{section_title}' not found."}

    content = section_node["content"]
    if not content.strip():
        return {"status": "error", "message": f"Section '{section_node['title']}' has no direct content. It only contains sub-sections."}

    summary = summarize_text(content, num_sentences)
    return {"status": "success", "data": f"### Summary of: {section_node['title']}\n\n{summary}"}
