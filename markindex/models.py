"""Data models and API standardizations for MarkIndex MCP."""

from typing import Any, TypedDict


class ToolResponse(TypedDict):
    """Standardized response format for all MCP tools."""
    success: bool
    data: Any
    error: str | None
    code: str | None


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
