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
def list_documents() -> dict:
    """List all ingested documents currently available in the index.

    Returns:
        Dict with status and data containing document metadata.
    """
    result: list[dict] = []
    for doc_id, doc in documents.items():
        result.append({
            "id": doc_id,
            "filename": doc.get("filename"),
            "filepath": doc.get("filepath"),
            "ingested_at": doc.get("ingested_at"),
            "size_chars": doc.get("size_chars"),
            "sections_count": len(doc.get("tree", [])),
        })

    logger.debug("list_documents returned %d items", len(result))
    return {"status": "success", "data": result}


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
        return {"status": "error", "message": f"Error deleting cache file: {exc}"}

    if deleted_mem or deleted_disk:
        logger.info("Deleted document '%s'", doc_id)
        return {"status": "success", "message": f"Successfully deleted document '{doc.get('filename')}' ({doc_id})"}

    return {"status": "error", "message": f"Document ID '{doc_id}' not found in index."}


@mcp.tool()
def save_to_outputs(filename: str, content: str) -> dict:
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
        
    if os.path.basename(filename) != filename:
        return {"status": "error", "message": "Error: Invalid filename path traversal detected."}

    safe_filename = "".join(c for c in filename if c.isalnum() or c in " ._-").strip()
    if not safe_filename:
        safe_filename = "unnamed_output.md"
        
    out_path = os.path.abspath(os.path.join(settings.OUTPUTS_DIR, safe_filename))
    outputs_dir_abs = os.path.abspath(settings.OUTPUTS_DIR)
    
    if not out_path.startswith(outputs_dir_abs):
        return {"status": "error", "message": "Error: Invalid filename path traversal detected."}
    
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("Saved generated output to %s", out_path)
        return {"status": "success", "message": f"Successfully saved output to {out_path}"}
    except Exception as exc:
        logger.error("Failed to save output: %s", exc)
        return {"status": "error", "message": f"Error saving output: {exc}"}
