"""Document ingestion tools for MarkIndex MCP.

Provides tools for ingesting documents from files, URLs, raw text,
YouTube transcripts, and entire directories.
"""

import os
import re
import uuid
import urllib.request
from datetime import datetime, timezone
from typing import Optional

from markindex.config import settings
from markindex.core.parser import parse_markdown_to_tree
from markindex.core.storage import save_document
from markindex.exceptions import IngestionError
from markindex.logger import get_logger
from markindex.server import mcp, md_converter, documents

logger = get_logger(__name__)


@mcp.tool()
def ingest_document(filepath: str) -> str:
    """Ingest a document (PDF, Word, HTML, etc.) or URL and build a searchable index.

    Converts the source to Markdown using MarkItDown, parses it into a
    hierarchical section tree, and persists the result to the local cache.

    Args:
        filepath: Local file path or URL (http/https) to the document.

    Returns:
        A dictionary with status and the new document ID.
    """
    is_url = filepath.startswith(("http://", "https://"))
    actual_filepath = filepath
    temp_file: Optional[str] = None

    try:
        if is_url:
            actual_filepath, temp_file = _download_url(filepath)
        else:
            actual_filepath = os.path.abspath(filepath)
            if not os.path.exists(actual_filepath):
                return {"status": "error", "message": f"File not found at {actual_filepath}"}

        result = md_converter.convert(actual_filepath)
        markdown_text = result.text_content

        doc_id = str(uuid.uuid4())
        filename = os.path.basename(filepath)
        now = datetime.now(timezone.utc).isoformat()

        tree = parse_markdown_to_tree(markdown_text)
        documents[doc_id] = {
            "markdown": markdown_text,
            "filepath": filepath,
            "filename": filename,
            "ingested_at": now,
            "size_chars": len(markdown_text),
            "tree": tree,
        }

        save_document(doc_id, {
            "filepath": filepath,
            "filename": filename,
            "ingested_at": now,
            "size_chars": len(markdown_text),
        }, markdown_text)

        logger.info("Ingested document '%s' as %s", filename, doc_id)
        return {"status": "success", "document_id": doc_id, "message": "Successfully ingested document."}

    except Exception as exc:
        logger.error("Ingestion failed for '%s': %s", filepath, exc)
        return {"status": "error", "message": f"Error ingesting document: {exc}"}
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass


@mcp.tool()
def ingest_text(title: str, text: str) -> str:
    """Ingest raw text or markdown directly into the index.

    Args:
        title: Human-readable title for the document.
        text: The raw text or markdown content.

    Returns:
        A dictionary with status and the new document ID.
    """
    try:
        doc_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        tree = parse_markdown_to_tree(text)

        documents[doc_id] = {
            "markdown": text,
            "filepath": f"RawText://{title}",
            "filename": title,
            "ingested_at": now,
            "size_chars": len(text),
            "tree": tree,
        }

        save_document(doc_id, {
            "filepath": f"RawText://{title}",
            "filename": title,
            "ingested_at": now,
            "size_chars": len(text),
        }, text)

        logger.info("Ingested text document '%s' as %s", title, doc_id)
        return {"status": "success", "document_id": doc_id, "message": "Successfully ingested text document."}

    except Exception as exc:
        logger.error("Text ingestion failed: %s", exc)
        return {"status": "error", "message": f"Error ingesting text: {exc}"}


@mcp.tool()
def ingest_youtube(url_or_id: str, interval_seconds: int = 120) -> str:
    """Ingest a YouTube video transcript into the index.

    Downloads the transcript using youtube-transcript-api, formats it into
    time-chunked Markdown sections, and indexes the result.

    Args:
        url_or_id: YouTube watch URL, share link, or 11-character video ID.
        interval_seconds: Time-chunk size in seconds (default 120).

    Returns:
        A dictionary with status and the new document ID.
    """
    video_id = _extract_youtube_id(url_or_id)
    if not video_id:
        return {"status": "error", "message": "Could not extract valid YouTube video ID."}

    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        video_title = _get_youtube_title(video_id)
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        markdown_text = _format_transcript(video_title, transcript, interval_seconds)

        doc_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        tree = parse_markdown_to_tree(markdown_text)

        yt_url = f"https://youtube.com/watch?v={video_id}"
        documents[doc_id] = {
            "markdown": markdown_text,
            "filepath": yt_url,
            "filename": video_title,
            "ingested_at": now,
            "size_chars": len(markdown_text),
            "tree": tree,
        }

        save_document(doc_id, {
            "filepath": yt_url,
            "filename": video_title,
            "ingested_at": now,
            "size_chars": len(markdown_text),
        }, markdown_text)

        logger.info("Ingested YouTube '%s' (%s) as %s", video_title, video_id, doc_id)
        return {"status": "success", "document_id": doc_id, "message": "Successfully ingested YouTube transcript."}

    except Exception as exc:
        logger.error("YouTube ingestion failed for '%s': %s", url_or_id, exc)
        return {"status": "error", "message": f"Error fetching or parsing YouTube transcript: {exc}"}


@mcp.tool()
def ingest_directory(directory_path: str) -> str:
    """Batch-ingest all supported documents from a local directory.

    Scans for files matching supported extensions and ingests each one.

    Args:
        directory_path: Absolute path to the target directory.

    Returns:
        A dictionary summarizing the ingestion results.
    """
    if not os.path.exists(directory_path):
        return {"status": "error", "message": f"Directory not found at {directory_path}"}
    if not os.path.isdir(directory_path):
        return {"status": "error", "message": f"Path {directory_path} is not a directory."}

    ingested: list[dict] = []
    failed: list[dict] = []

    for entry in os.scandir(directory_path):
        if not entry.is_file():
            continue
        ext = os.path.splitext(entry.name)[1].lower()
        if ext not in settings.SUPPORTED_EXTENSIONS:
            continue

        res = ingest_document(entry.path)
        if isinstance(res, dict) and res.get("status") == "success":
            doc_id = res.get("document_id", "unknown")
            ingested.append({"filename": entry.name, "filepath": entry.path, "document_id": doc_id})
        else:
            failed.append({"filename": entry.name, "error": str(res)})

    logger.info("Directory ingestion: %d succeeded, %d failed in %s", len(ingested), len(failed), directory_path)
    return {
        "status": "success",
        "directory_path": directory_path,
        "successfully_ingested": ingested,
        "failed_ingested": failed,
        "total_success": len(ingested),
        "total_failed": len(failed),
    }


# ── Private Helpers ────────────────────────────────────────────────

def _download_url(url: str) -> tuple[str, str]:
    """Download a URL to a temporary file with strict checks."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https schemes are supported.")

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    max_size = 50 * 1024 * 1024  # 50 MB
    content = bytearray()
    
    with urllib.request.urlopen(req, timeout=15) as response:
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > max_size:
            raise ValueError(f"File too large: {content_length} bytes (max {max_size})")

        content_type = response.headers.get("Content-Type", "").lower()
        if any(bad in content_type for bad in ("video/", "audio/", "application/octet-stream")):
            raise ValueError(f"Unsupported content type: {content_type}")

        while True:
            chunk = response.read(8192)
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > max_size:
                raise ValueError("Download exceeded maximum allowed size (50MB).")

    suffix = ".html"
    last_part = url.split("/")[-1]
    if "." in last_part:
        suffix = "." + last_part.split(".")[-1]

    temp_dir = os.path.join(settings.RAW_DIR, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_file = os.path.join(temp_dir, f"dl_{uuid.uuid4().hex}{suffix}")
    with open(temp_file, "wb") as f:
        f.write(content)
    return temp_file, temp_file


def _extract_youtube_id(url_or_id: str) -> Optional[str]:
    """Extract an 11-character YouTube video ID from various URL formats."""
    url_or_id = url_or_id.strip()
    if len(url_or_id) == 11 and re.match(r"^[0-9A-Za-z_-]{11}$", url_or_id):
        return url_or_id
    match = re.search(
        r"(?:v=|/embed/|/watch\?v=|/\d{1,2}/|/v/|youtu\.be/|youtube\.com/shorts/)"
        r"([0-9A-Za-z_-]{11})",
        url_or_id,
    )
    return match.group(1) if match else None


def _get_youtube_title(video_id: str) -> str:
    """Fetch the video title from YouTube's watch page."""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode("utf-8")
        match = re.search(r"<title>(.*?)</title>", html)
        if match:
            title = match.group(1).strip()
            return title.removesuffix(" - YouTube")
    except Exception:
        pass
    return f"YouTube Video {video_id}"


def _format_transcript(
    title: str, transcript: list[dict], interval_seconds: int
) -> str:
    """Format a YouTube transcript into time-chunked Markdown."""
    def _ts(seconds: float) -> str:
        return f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"

    md_lines = [f"# {title}\n"]
    current_interval = 0
    current_lines: list[str] = []

    for item in transcript:
        idx = int(item["start"] // interval_seconds)
        if idx > current_interval:
            s, e = _ts(current_interval * interval_seconds), _ts((current_interval + 1) * interval_seconds)
            md_lines.append(f"## {s} - {e}\n")
            md_lines.append(" ".join(current_lines) + "\n")
            current_interval = idx
            current_lines = [item["text"]]
        else:
            current_lines.append(item["text"])

    if current_lines:
        s, e = _ts(current_interval * interval_seconds), _ts((current_interval + 1) * interval_seconds)
        md_lines.append(f"## {s} - {e}\n")
        md_lines.append(" ".join(current_lines) + "\n")

    return "\n".join(md_lines)
