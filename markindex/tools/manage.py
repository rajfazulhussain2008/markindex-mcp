"""Document management tools for MarkIndex MCP.

Provides tools for listing and deleting ingested documents.
"""

import os
from typing import Any

from markindex.config import settings
from markindex.core.storage import delete_document_file
from markindex.exceptions import DocumentNotFoundError
from markindex.logger import get_logger
from markindex.server import mcp, documents

logger = get_logger(__name__)


@mcp.tool()
def list_documents() -> dict[str, Any]:
    """List all ingested documents currently available in the index.

    Returns:
        Dict with success status and list of documents.
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
    return {"success": True, "data": result, "error": None, "code": None}


@mcp.tool()
def delete_document(doc_id: str) -> dict[str, Any]:
    """Delete a document from the index and remove its cache file.

    Args:
        doc_id: The unique document ID.

    Returns:
        Dict with success status.
    """
    doc = documents.get(doc_id)
    if not doc:
        return {"success": False, "data": None, "error": f"Document ID '{doc_id}' not found in index.", "code": "DOC_NOT_FOUND"}

    deleted_mem = False
    if doc_id in documents:
        del documents[doc_id]
        deleted_mem = True

    deleted_disk = False
    try:
        deleted_disk = delete_document_file(doc_id)
    except Exception as exc:
        logger.error("Failed to delete cache file for %s: %s", doc_id, exc)
        return {"success": False, "data": None, "error": f"Error deleting cache file: {exc}", "code": "DELETE_ERROR"}

    logger.info("Deleted document '%s'", doc_id)
    return {"success": True, "data": {"deleted_id": doc_id, "filename": doc.get("filename")}, "error": None, "code": None}


@mcp.tool()
def save_to_outputs(filename: str, content: str) -> dict[str, Any]:
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
        return {"success": False, "data": None, "error": "Invalid filename path traversal detected.", "code": "PATH_TRAVERSAL"}

    safe_filename = "".join(c for c in filename if c.isalnum() or c in " ._-").strip()
    if not safe_filename:
        return {"success": False, "data": None, "error": "Filename contains only invalid characters.", "code": "INVALID_FILENAME"}
        
    out_path = os.path.abspath(os.path.join(settings.OUTPUTS_DIR, safe_filename))
    outputs_dir_abs = os.path.abspath(settings.OUTPUTS_DIR)
    
    if not out_path.startswith(outputs_dir_abs):
        return {"success": False, "data": None, "error": "Invalid filename path traversal detected.", "code": "PATH_TRAVERSAL"}
    
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("Saved generated output to %s", out_path)
        return {"success": True, "data": {"saved_path": out_path}, "error": None, "code": None}
    except Exception as exc:
        logger.error("Failed to save output: %s", exc)
        return {"success": False, "data": None, "error": f"Error saving output: {exc}", "code": "SAVE_ERROR"}
