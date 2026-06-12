"""Persistent storage layer for MarkIndex MCP.

Handles serialization and deserialization of documents using Markdown files
with YAML-style frontmatter headers for metadata.
"""

import os
from typing import Any

from markindex.config import settings
from markindex.logger import get_logger

logger = get_logger(__name__)


def parse_frontmatter(file_content: str) -> tuple[dict[str, Any], str]:
    """Parse a markdown file with YAML-style frontmatter.

    Args:
        file_content: Raw file content string.

    Returns:
        Tuple of (metadata_dict, markdown_content).
    """
    metadata: dict[str, Any] = {}
    markdown_content = file_content

    if file_content.startswith("---"):
        parts = file_content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    metadata[k.strip()] = v.strip()
            markdown_content = parts[2].strip()

    if "size_chars" in metadata:
        try:
            metadata["size_chars"] = int(metadata["size_chars"])
        except ValueError:
            metadata["size_chars"] = 0

    return metadata, markdown_content


def serialize_frontmatter(metadata: dict[str, Any], markdown_content: str) -> str:
    """Serialize metadata and content into a markdown file with frontmatter.

    Args:
        metadata: Key-value metadata pairs.
        markdown_content: The markdown document body.

    Returns:
        Complete file content string with frontmatter header.
    """
    lines = ["---"]
    for k, v in metadata.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + markdown_content.strip()


def save_document(doc_id: str, metadata: dict[str, Any], markdown_content: str) -> str:
    """Persist a document to the wiki cache directory.

    Args:
        doc_id: Unique document identifier.
        metadata: Document metadata.
        markdown_content: The markdown body.

    Returns:
        Absolute path to the saved cache file.
    """
    cache_path = os.path.join(settings.WIKI_DIR, f"{doc_id}.md")
    serialized = serialize_frontmatter(metadata, markdown_content)
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(serialized)
    logger.info("Saved document '%s' → %s", metadata.get("filename", doc_id), cache_path)
    _generate_wiki_index()
    return cache_path


def delete_document_file(doc_id: str) -> bool:
    """Remove a document's cache file from disk.

    Args:
        doc_id: Unique document identifier.

    Returns:
        True if the file was deleted, False if it did not exist.
    """
    cache_path = os.path.join(settings.WIKI_DIR, f"{doc_id}.md")
    if os.path.exists(cache_path):
        os.remove(cache_path)
        logger.info("Deleted cache file: %s", cache_path)
        _generate_wiki_index()
        return True
    return False


def load_all_documents() -> dict[str, tuple[dict[str, Any], str]]:
    """Load all cached documents from disk.

    Returns:
        Dict mapping doc_id to (metadata, markdown_content) tuples.
    """
    documents: dict[str, tuple[dict[str, Any], str]] = {}

    if not os.path.exists(settings.WIKI_DIR):
        return documents

    for filename in os.listdir(settings.WIKI_DIR):
        if not filename.endswith(".md") or filename == "index.md":
            continue
        doc_id = filename[:-3]
        filepath = os.path.join(settings.WIKI_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            metadata, markdown = parse_frontmatter(content)
            documents[doc_id] = (metadata, markdown)
            logger.debug("Loaded cache: %s (%s)", filename, metadata.get("filename", "Unknown"))
        except Exception as exc:
            logger.error("Failed to load %s: %s", filename, exc)

    logger.info("Loaded %d documents from disk cache", len(documents))
    return documents


def _generate_wiki_index() -> None:
    """Generate the master index.md map in the wiki directory."""
    index_path = os.path.join(settings.WIKI_DIR, "index.md")
    lines = [
        "# 📚 Master Knowledge Index",
        "",
        "This is the auto-generated index of all documents currently ingested in the system.",
        ""
    ]

    for filename in os.listdir(settings.WIKI_DIR):
        if not filename.endswith(".md") or filename == "index.md":
            continue
        
        filepath = os.path.join(settings.WIKI_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            metadata, _ = parse_frontmatter(content)
            title = metadata.get("filename", filename)
            doc_id = filename[:-3]
            lines.append(f"- [{title}]({filename}) (ID: `{doc_id}`)")
        except Exception:
            pass

    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.debug("Updated wiki/index.md")
