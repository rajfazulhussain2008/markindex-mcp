"""Custom exception hierarchy for MarkIndex MCP.

All domain-specific errors inherit from :class:`MarkIndexError` to allow
callers to catch broad or narrow exception categories.
"""


class MarkIndexError(Exception):
    """Base exception for all MarkIndex operations."""


class DocumentNotFoundError(MarkIndexError):
    """Raised when a document ID does not exist in the index."""

    def __init__(self, doc_id: str) -> None:
        self.doc_id = doc_id
        super().__init__(f"Document not found: {doc_id}")


class SectionNotFoundError(MarkIndexError):
    """Raised when a section title cannot be resolved in a document tree."""

    def __init__(self, section_title: str, suggestions: list[str] | None = None) -> None:
        self.section_title = section_title
        self.suggestions = suggestions or []
        msg = f"Section not found: '{section_title}'"
        if self.suggestions:
            msg += "\nDid you mean: " + ", ".join(self.suggestions)
        super().__init__(msg)


class IngestionError(MarkIndexError):
    """Raised when a document fails to be ingested."""


class SearchError(MarkIndexError):
    """Raised when a search operation fails."""
