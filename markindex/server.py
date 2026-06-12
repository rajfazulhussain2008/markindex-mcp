"""FastMCP server initialization and lifecycle management.

This module is the central hub that:
1. Creates the FastMCP server instance and MarkItDown converter.
2. Exposes shared state (``documents``) for tool modules.
3. Loads persisted documents from disk on startup.
4. Registers all tool modules.
5. Provides the ``main()`` entry point.
"""

from markitdown import MarkItDown
from mcp.server.fastmcp import FastMCP

from markindex.config import settings
from markindex.core.parser import parse_markdown_to_tree
from markindex.core.storage import load_all_documents
from markindex.logger import get_logger

logger = get_logger(__name__)

# ── Server Instance ────────────────────────────────────────────────
mcp = FastMCP("MarkIndex")

# ── Shared State ───────────────────────────────────────────────────
md_converter = MarkItDown()
documents: dict[str, dict] = {}


def _load_cache() -> None:
    """Load all persisted documents from the disk cache into memory."""
    cached = load_all_documents()
    for doc_id, (metadata, markdown) in cached.items():
        documents[doc_id] = {
            "markdown": markdown,
            "filepath": metadata.get("filepath", "Unknown"),
            "filename": metadata.get("filename", "Unknown"),
            "ingested_at": metadata.get("ingested_at", "Unknown"),
            "size_chars": metadata.get("size_chars", len(markdown)),
            "tree": parse_markdown_to_tree(markdown),
            "metadata": metadata,
        }
    if cached:
        logger.info("Restored %d documents from cache", len(cached))


def _register_tools() -> None:
    """Import tool modules to register their @mcp.tool() functions."""
    import markindex.tools.ingest  # noqa: F401
    import markindex.tools.manage  # noqa: F401
    import markindex.tools.navigate  # noqa: F401
    import markindex.tools.query  # noqa: F401

    logger.debug("All tool modules registered")


def main() -> None:
    """Boot the MarkIndex MCP server."""
    logger.info("Starting MarkIndex MCP v2.0.0")
    logger.info("Raw Directory: %s", settings.RAW_DIR)
    logger.info("Wiki Directory: %s", settings.WIKI_DIR)
    logger.info("Outputs Directory: %s", settings.OUTPUTS_DIR)

    _load_cache()
    _register_tools()

    logger.info("Server ready — listening for connections")
    mcp.run()


if __name__ == "__main__":
    main()
