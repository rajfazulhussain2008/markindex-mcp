"""Document ingestion tools for MarkIndex MCP.

Provides tools for ingesting documents from files, URLs, raw text,
YouTube transcripts, and entire directories.
"""

import os
import re
import tempfile
import urllib.parse
import urllib.request
import uuid
from datetime import UTC, datetime

from markindex.config import settings
from markindex.core.parser import parse_markdown_to_tree
from markindex.core.storage import save_document
from markindex.logger import get_logger
from markindex.models import ToolResponse, err, ok
from markindex.server import documents, mcp, md_converter

logger = get_logger(__name__)


@mcp.tool()
def ingest_document(filepath: str) -> ToolResponse:
    """Ingest a single document into the system from a local file or URL.

    Args:
        filepath: Absolute local path or HTTP(S) URL.

    Returns:
        Dict with success status, document ID, and other details.
    """
    is_url = filepath.startswith(("http://", "https://"))
    actual_filepath = filepath
    temp_file: str | None = None

    try:
        if is_url:
            actual_filepath, temp_file = _download_url(filepath)
        else:
            actual_filepath = os.path.realpath(filepath)
            if not os.path.exists(actual_filepath):
                return err(f"File not found at {actual_filepath}", "FILE_NOT_FOUND")
            
            if not settings.ALLOW_EXTERNAL_FILES:
                raw_dir_abs = os.path.realpath(settings.RAW_DIR)
                if os.path.commonpath([actual_filepath, raw_dir_abs]) != raw_dir_abs:
                    return err("External file ingestion disabled. File must be inside RAW_DIR.", "ACCESS_DENIED")

        result = md_converter.convert(actual_filepath)
        markdown_text = result.text_content

        doc_id = str(uuid.uuid4())
        filename = os.path.basename(filepath)
        now = datetime.now(UTC).isoformat()

        metadata = {
            "filepath": filepath,
            "filename": filename,
            "ingested_at": now,
            "size_chars": len(markdown_text),
        }

        cache_path = save_document(doc_id, metadata, markdown_text)
        tree = parse_markdown_to_tree(markdown_text)
        
        documents[doc_id] = {
            "markdown": markdown_text,
            "filepath": metadata["filepath"],
            "filename": metadata["filename"],
            "ingested_at": metadata["ingested_at"],
            "size_chars": metadata["size_chars"],
            "tree": tree,
            "metadata": metadata
        }

        logger.info("Successfully ingested document '%s' -> ID: %s", metadata["filename"], doc_id)
        return ok({"document_id": doc_id, "cache_path": cache_path, "metadata": metadata})

    except Exception as exc:
        logger.error("Failed to ingest %s: %s", filepath, exc)
        return err(str(exc), "INGESTION_ERROR")
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass


@mcp.tool()
def ingest_text(title: str, text: str) -> ToolResponse:
    """Ingest raw text or markdown directly into the index.

    Args:
        title: Human-readable title for the document.
        text: The raw text or markdown content.

    Returns:
        A dictionary with status and the new document ID.
    """
    try:
        doc_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        tree = parse_markdown_to_tree(text)

        metadata = {
            "filepath": f"RawText://{title}",
            "filename": title,
            "ingested_at": now,
            "size_chars": len(text),
        }

        documents[doc_id] = {
            "markdown": text,
            "filepath": metadata["filepath"],
            "filename": metadata["filename"],
            "ingested_at": metadata["ingested_at"],
            "size_chars": metadata["size_chars"],
            "tree": tree,
            "metadata": metadata
        }

        cache_path = save_document(doc_id, metadata, text)

        logger.info("Ingested text document '%s' as %s", title, doc_id)
        return ok({"document_id": doc_id, "cache_path": cache_path, "metadata": metadata})

    except Exception as exc:
        logger.error("Text ingestion failed: %s", exc)
        return err(str(exc), "INGESTION_ERROR")


@mcp.tool()
def ingest_youtube(url_or_id: str, interval_seconds: int = 120) -> ToolResponse:
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
        return err("Could not extract valid YouTube video ID.", "INVALID_YOUTUBE_ID")

    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        video_title = _get_youtube_title(video_id)
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        markdown_text = _format_transcript(video_title, transcript, interval_seconds)

        doc_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        tree = parse_markdown_to_tree(markdown_text)

        yt_url = f"https://youtube.com/watch?v={video_id}"
        metadata = {
            "filepath": yt_url,
            "filename": f"YouTube - {video_title}",
            "ingested_at": now,
            "size_chars": len(markdown_text),
        }

        documents[doc_id] = {
            "markdown": markdown_text,
            "filepath": metadata["filepath"],
            "filename": metadata["filename"],
            "ingested_at": metadata["ingested_at"],
            "size_chars": metadata["size_chars"],
            "tree": tree,
            "metadata": metadata
        }

        cache_path = save_document(doc_id, metadata, markdown_text)

        logger.info("Ingested YouTube transcript for '%s' as %s", video_title, doc_id)
        return ok({"document_id": doc_id, "cache_path": cache_path, "metadata": metadata})

    except Exception as exc:
        logger.error("YouTube ingestion failed: %s", exc)
        return err(str(exc), "YOUTUBE_ERROR")


@mcp.tool()
def ingest_directory(dir_path: str) -> ToolResponse:
    """Ingest all supported documents in a directory.

    Args:
        dir_path: Absolute path to the directory.

    Returns:
        Dict with success status and summary of ingested vs failed files.
    """
    actual_path = os.path.realpath(dir_path)
    if not os.path.isdir(actual_path):
        return err(f"Directory not found: {actual_path}", "DIR_NOT_FOUND")

    if not settings.ALLOW_EXTERNAL_FILES:
        raw_dir_abs = os.path.realpath(settings.RAW_DIR)
        if os.path.commonpath([actual_path, raw_dir_abs]) != raw_dir_abs:
            return err("External directory ingestion disabled.", "ACCESS_DENIED")

    results = {"ingested": [], "failed": []}

    for entry in os.scandir(actual_path):
        if not entry.is_file():
            continue
        ext = os.path.splitext(entry.name)[1].lower()
        if ext not in settings.SUPPORTED_EXTENSIONS:
            continue

        res = ingest_document(entry.path)
        if res.get("success"):
            results["ingested"].append({"filename": entry.name, "document_id": res["data"]["document_id"]})
        else:
            results["failed"].append({"file": entry.name, "error": res.get("error")})

    logger.info("Directory ingestion complete. Success: %d, Failed: %d",
                len(results["ingested"]), len(results["failed"]))
    return ok(results)


# ── Private Helpers ────────────────────────────────────────────────

def _download_url(url: str) -> tuple[str, str]:
    """Download a URL to a temporary file with strict checks."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https schemes are supported.")

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    max_size = settings.MAX_FILE_MB * 1024 * 1024
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
                raise ValueError(f"Download exceeded maximum allowed size ({settings.MAX_FILE_MB}MB).")

    # Sanitize suffix
    suffix = ""
    basename = os.path.basename(parsed.path)
    if "." in basename:
        extracted = "." + basename.split(".")[-1].lower()
        if extracted in settings.SUPPORTED_EXTENSIONS:
            suffix = extracted

    # Fallback to content-type mapping if missing or invalid
    if not suffix:
        if "pdf" in content_type:
            suffix = ".pdf"
        elif "html" in content_type:
            suffix = ".html"
        else:
            suffix = ".txt"

    fd, temp_path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(content)
    return temp_path, temp_path


def _extract_youtube_id(url_or_id: str) -> str | None:
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
