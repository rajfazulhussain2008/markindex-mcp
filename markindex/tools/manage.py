"""Document management tools for MarkIndex MCP.

Provides tools for listing and deleting ingested documents.
"""

import os
from datetime import UTC

from markindex.config import settings
from markindex.core.storage import delete_document_file
from markindex.logger import get_logger
from markindex.models import ToolResponse, err, ok
from markindex.server import documents, mcp

logger = get_logger(__name__)


@mcp.tool()
def list_documents() -> ToolResponse:
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
    return ok(result)


@mcp.tool()
def delete_document(doc_id: str) -> ToolResponse:
    """Delete a document from the index and remove its cache file.

    Args:
        doc_id: The unique document ID.

    Returns:
        Dict with success status.
    """
    doc = documents.get(doc_id)
    if not doc:
        return err(f"Document ID '{doc_id}' not found in index.", "DOC_NOT_FOUND")

    if doc_id in documents:
        del documents[doc_id]

    try:
        delete_document_file(doc_id)
    except Exception as exc:
        logger.error("Failed to delete cache file for %s: %s", doc_id, exc)
        return err(f"Error deleting cache file: {exc}", "DELETE_ERROR")

    logger.info("Deleted document '%s'", doc_id)
    return ok({"deleted_id": doc_id, "filename": doc.get("filename")})


@mcp.tool()
def save_to_outputs(filename: str, content: str) -> ToolResponse:
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
        return err("Invalid filename path traversal detected.", "PATH_TRAVERSAL")

    safe_filename = "".join(c for c in filename if c.isalnum() or c in " ._-").strip()
    if not safe_filename:
        return err("Filename contains only invalid characters.", "INVALID_FILENAME")
        
    out_path = os.path.realpath(os.path.join(settings.OUTPUTS_DIR, safe_filename))
    outputs_dir_abs = os.path.realpath(settings.OUTPUTS_DIR)
    
    if os.path.commonpath([out_path, outputs_dir_abs]) != outputs_dir_abs:
        return err("Invalid filename path traversal detected.", "PATH_TRAVERSAL")
    
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("Saved generated output to %s", out_path)
        return ok({"saved_path": out_path})
    except Exception as exc:
        logger.error("Failed to save output: %s", exc)
        return err(f"Error saving output: {exc}", "SAVE_ERROR")

@mcp.tool()
def get_server_status() -> ToolResponse:
    """Get the current health, status, and memory stats of the MarkIndex MCP server.

    Returns:
        Dict with version, uptime info, and memory index statistics.
    """
    from datetime import datetime
    return ok({
        "version": "2.0.0",
        "timestamp": datetime.now(UTC).isoformat(),
        "documents_indexed": len(documents),
        "total_size_chars": sum(doc.get("size_chars", 0) for doc in documents.values()),
        "status": "online"
    })
