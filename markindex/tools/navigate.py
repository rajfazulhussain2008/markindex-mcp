"""Section navigation tools for MarkIndex MCP.

Provides tools for traversing the document tree using sibling and
parent navigation, reading sections, and generating extractive summaries.
"""


from markindex.core.parser import find_section, get_flat_navigation_map, section_to_markdown
from markindex.core.summarizer import summarize_text
from markindex.exceptions import DocumentNotFoundError
from markindex.logger import get_logger
from markindex.models import ToolResponse, err, ok
from markindex.server import documents, mcp

logger = get_logger(__name__)


def _require_document(doc_id: str) -> dict:
    if doc_id not in documents:
        raise DocumentNotFoundError(doc_id)
    return documents[doc_id]


@mcp.tool()
def get_adjacent_sections(doc_id: str, section_title: str) -> ToolResponse:
    """Retrieve navigation context for a section.

    Returns the parent, previous, and next sections relative to
    the specified section.

    Args:
        doc_id: The document ID.
        section_title: Section title, full path, or section ID.

    Returns:
        Dict with status and data containing navigation context.
    """
    try:
        doc = _require_document(doc_id)
    except DocumentNotFoundError as exc:
        return err(str(exc), "DOC_NOT_FOUND")

    tree = doc["tree"]
    section_node = find_section(tree, section_title)
    if not section_node:
        return err(f"Section '{section_title}' not found.", "SECTION_NOT_FOUND")

    nav_map = get_flat_navigation_map(tree)
    node_id = section_node["id"]

    if node_id not in nav_map:
        return err(f"Navigation mapping failed for '{node_id}'.", "MAP_FAILED")

    return ok(nav_map[node_id])


@mcp.tool()
def summarize_section(doc_id: str, section_title: str, num_sentences: int = 5) -> ToolResponse:
    """Generate an extractive summary of a document section.

    Uses term-frequency scoring to select the most informative sentences.

    Args:
        doc_id: The document ID.
        section_title: Section title, full path, or section ID.
        num_sentences: Number of sentences to include in the summary.

    Returns:
        Dict with status and the summary text.
    """
    try:
        doc = _require_document(doc_id)
    except DocumentNotFoundError as exc:
        return err(str(exc), "DOC_NOT_FOUND")

    tree = doc["tree"]
    section_node = find_section(tree, section_title)
    if not section_node:
        return err(f"Section '{section_title}' not found.", "SECTION_NOT_FOUND")

    markdown_content = section_to_markdown(section_node)
    
    if len(markdown_content) < 500:
        return ok({"summary": markdown_content, "note": "Section is already short."})

    try:
        summary = summarize_text(markdown_content, num_sentences)
        return ok({"summary": summary})
    except Exception as exc:
        logger.error("Summarization failed for %s: %s", section_title, exc)
        return err(f"Summarization failed: {exc}", "SUMMARY_FAILED")
