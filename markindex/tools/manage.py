"""Document management tools for MarkIndex MCP.

Provides tools for listing and deleting ingested documents.
"""

import json
import os

from markindex.config import settings
from markindex.core.storage import delete_document_file
from markindex.exceptions import DocumentNotFoundError
from markindex.logger import get_logger
from markindex.server import mcp, documents

logger = get_logger(__name__)


@mcp.tool()
def list_documents() -> str:
    """List all ingested documents currently available in the index.

    Returns:
        JSON array of document metadata objects.
    """
    doc_list = [
        {
            "document_id": doc_id,
            "filename": doc.get("filename", "Unknown"),
            "filepath": doc.get("filepath", "Unknown"),
            "ingested_at": doc.get("ingested_at", "Unknown"),
            "size_chars": doc.get("size_chars", 0),
        }
        for doc_id, doc in documents.items()
    ]
    return json.dumps(doc_list, indent=2)


@mcp.tool()
def delete_document(doc_id: str) -> str:
    """Delete a document from the in-memory index and disk cache.

    Args:
        doc_id: The document ID to delete.

    Returns:
        Confirmation or error message.
    """
    deleted_mem = doc_id in documents
    if deleted_mem:
        del documents[doc_id]

    try:
        deleted_disk = delete_document_file(doc_id)
    except Exception as exc:
        logger.error("Failed to delete cache file for %s: %s", doc_id, exc)
        return f"Error deleting cache file: {exc}"

    if deleted_mem or deleted_disk:
        logger.info("Deleted document '%s'", doc_id)
        return f"Successfully deleted document '{doc_id}'."

    return f"Error: Document '{doc_id}' not found."


@mcp.tool()
def save_to_outputs(filename: str, content: str) -> str:
    """Save an AI-generated report or content to the outputs/ folder.

    This tool permanently persists generated knowledge into the 3-folder system.

    Args:
        filename: The desired filename (e.g., 'summary_report.md').
        content: The text/markdown content to save.

    Returns:
        Confirmation message with the saved path.
    """
    if not filename.endswith(".md") and not filename.endswith(".txt"):
        filename += ".md"
        
    safe_filename = "".join(c for c in filename if c.isalnum() or c in " ._-").strip()
    if not safe_filename:
        safe_filename = "unnamed_output.md"
        
    out_path = os.path.join(settings.OUTPUTS_DIR, safe_filename)
    
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("Saved generated output to %s", out_path)
        return f"Successfully saved output to {out_path}"
    except Exception as exc:
        logger.error("Failed to save output '%s': %s", out_path, exc)
        return f"Error saving output: {exc}"
