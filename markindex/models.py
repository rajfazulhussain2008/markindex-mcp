"""Data models and API standardizations for MarkIndex MCP."""

from typing import Any, TypedDict


class ToolResponse(TypedDict):
    """Standardized response format for all MCP tools."""

    success: bool
    data: Any
    error: str | None
    code: str | None


class SectionNode(TypedDict):
    """Represents a parsed markdown section."""

    level: int
    title: str
    content: str
    children: list["SectionNode"]


class DocumentMetadata(TypedDict):
    """Metadata describing an ingested document."""

    filepath: str
    filename: str
    ingested_at: str
    size_chars: int


class DocumentRecord(TypedDict):
    """The internal representation of a document stored in memory."""

    markdown: str
    filepath: str
    filename: str
    ingested_at: str
    size_chars: int
    tree: list[SectionNode]
    metadata: DocumentMetadata


def ok(data: Any = None) -> ToolResponse:
    """Return a successful ToolResponse.

    Args:
        data: The payload data to return.
    """
    return {
        "success": True,
        "data": data,
        "error": None,
        "code": None,
    }


def err(message: str, code: str) -> ToolResponse:
    """Return an error ToolResponse.

    Args:
        message: The human-readable error message.
        code: A short machine-readable error code string.
    """
    return {
        "success": False,
        "data": None,
        "error": message,
        "code": code,
    }
