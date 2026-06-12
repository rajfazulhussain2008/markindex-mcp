"""Document querying tools for MarkIndex MCP.

Provides tools for retrieving document outlines, reading specific sections
with pagination, and performing TF-IDF ranked searches.
"""

import difflib

from markindex.config import settings
from markindex.core.parser import (
    find_section,
    get_outline,
    section_to_markdown,
)
from markindex.core.search import rank_sections_tfidf
from markindex.exceptions import DocumentNotFoundError
from markindex.logger import get_logger
from markindex.models import ToolResponse, err, ok
from markindex.server import documents, mcp

logger = get_logger(__name__)


def _require_document(doc_id: str) -> dict:
    """Validate and retrieve a document by ID."""
    if doc_id not in documents:
        raise DocumentNotFoundError(doc_id)
    return documents[doc_id]


@mcp.tool()
def get_document_outline(doc_id: str) -> ToolResponse:
    """Retrieve the hierarchical outline (Table of Contents) of an ingested document.

    Args:
        doc_id: The document ID returned by an ingestion tool.

    Returns:
        Dict with status and hierarchical outline data.
    """
    try:
        doc = _require_document(doc_id)
    except DocumentNotFoundError as exc:
        return err(str(exc), "DOC_NOT_FOUND")

    return ok(get_outline(doc["tree"]))


@mcp.tool()
def read_section(
    doc_id: str,
    section_title: str,
    start_char: int = 0,
    max_chars: int | None = None,
) -> ToolResponse:
    """Read the content of a specific section with optional pagination.

    Supports exact, partial, and fuzzy title matching.

    Args:
        doc_id: The document ID.
        section_title: Section title, full path, or section ID.
        start_char: Starting character offset for pagination.
        max_chars: Maximum characters to return (None for all).

    Returns:
        Dict with success status and markdown content (paginated).
    """
    try:
        doc = _require_document(doc_id)
    except DocumentNotFoundError as exc:
        return err(str(exc), "DOC_NOT_FOUND")

    tree = doc["tree"]
    section_node = find_section(tree, section_title)

    if not section_node:
        msg = _section_not_found_message(tree, section_title)
        return err(msg, "SECTION_NOT_FOUND")

    full_md = section_to_markdown(section_node)
    total_len = len(full_md)

    start_char = max(0, start_char)
    if start_char >= total_len:
        return err(f"start_char {start_char} exceeds section length {total_len}.", "OUT_OF_BOUNDS")

    end_char = total_len
    if max_chars is not None and max_chars > 0:
        end_char = min(total_len, start_char + max_chars)

    page = full_md[start_char:end_char]

    if total_len > len(page):
        remaining = total_len - end_char
        page += (
            f"\n\n--- [Showing characters {start_char}-{end_char} of {total_len}. "
            f"Remaining: {remaining} characters. "
            f"Use start_char={end_char} to read next page.] ---"
        )

    return ok(page)


@mcp.tool()
def search_sections(doc_id: str, query: str, is_regex: bool = False, limit: int | None = None) -> ToolResponse:
    """Search across all sections using TF-IDF relevance ranking.

    Args:
        doc_id: The document ID.
        query: Search query or regular expression.
        is_regex: If True, treat query as a regex pattern.
        limit: Max number of results to return. Defaults to settings.MAX_SEARCH_RESULTS.

    Returns:
        Dict with status and list of matching sections.
    """
    try:
        doc = _require_document(doc_id)
    except DocumentNotFoundError as exc:
        return err(str(exc), "DOC_NOT_FOUND")

    matches = rank_sections_tfidf(doc["tree"], query, is_regex)
    actual_limit = limit if limit is not None else settings.MAX_SEARCH_RESULTS
    matches = matches[:actual_limit]
    logger.info("Search '%s' in %s returned %d results", query, doc_id[:8], len(matches))
    return ok(matches)


def _section_not_found_message(tree: list[dict], section_title: str) -> str:
    """Generate a helpful error message with suggestions."""
    all_titles: list[str] = []

    def _collect(nodes: list[dict]) -> None:
        for n in nodes:
            all_titles.append(n["title"])
            _collect(n["children"])

    _collect(tree)
    close = difflib.get_close_matches(section_title, all_titles, n=3, cutoff=0.3)

    if close:
        suggestion = "\nDid you mean one of these?\n" + "\n".join(f"- {t}" for t in close)
    else:
        top = [n["title"] for n in tree]
        suggestion = "\nTop-level sections available:\n" + "\n".join(f"- {t}" for t in top)

    return f"Error: Section '{section_title}' not found.{suggestion}"
