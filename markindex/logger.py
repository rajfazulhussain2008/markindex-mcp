"""Structured logging configuration for MarkIndex MCP.

Provides a pre-configured logger with consistent formatting across all modules.
Log level is controlled via the MARKINDEX_LOG_LEVEL environment variable.
"""

import logging
import sys

from markindex.config import settings

_LOG_FORMAT = "%(asctime)s │ %(levelname)-8s │ %(name)-24s │ %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """Create and return a named logger with standardized formatting.

    Args:
        name: The logger name, typically ``__name__`` of the calling module.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        logger.addHandler(handler)

    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    return logger
