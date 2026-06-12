"""Centralized configuration management for MarkIndex MCP.

All runtime settings are managed through a single Settings dataclass.
Values can be overridden via environment variables prefixed with MARKINDEX_.
"""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application-wide configuration.

    Attributes:
        DATA_DIR: Directory for persistent markdown cache storage.
        LOG_LEVEL: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        MAX_SEARCH_RESULTS: Maximum number of search results returned.
        DEFAULT_SUMMARY_SENTENCES: Default sentence count for extractive summaries.
        DEFAULT_YOUTUBE_INTERVAL: Default time-chunk interval for YouTube transcripts.
        SUPPORTED_EXTENSIONS: File extensions accepted by the directory ingestion tool.
    """

    DATA_DIR: str = field(default_factory=lambda: os.environ.get(
        "MARKINDEX_DATA_DIR",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    ))
    LOG_LEVEL: str = field(default_factory=lambda: os.environ.get("MARKINDEX_LOG_LEVEL", "INFO"))
    MAX_SEARCH_RESULTS: int = 50
    DEFAULT_SUMMARY_SENTENCES: int = 5
    DEFAULT_YOUTUBE_INTERVAL: int = 120
    SUPPORTED_EXTENSIONS: tuple = (
        ".pdf", ".docx", ".doc", ".xlsx", ".pptx",
        ".html", ".htm", ".txt", ".md",
    )

    def __post_init__(self) -> None:
        """Ensure the data directory exists on initialization."""
        os.makedirs(self.DATA_DIR, exist_ok=True)


settings = Settings()
