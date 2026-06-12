"""Extractive text summarizer for MarkIndex MCP.

Uses term-frequency sentence scoring to extract the most informative
sentences from a body of text.
"""

import re

from markindex.core.search import tokenize
from markindex.logger import get_logger

logger = get_logger(__name__)


def summarize_text(text: str, num_sentences: int = 5) -> str:
    """Extract the top N most informative sentences from text.

    Args:
        text: The input text to summarize.
        num_sentences: Number of sentences to extract.

    Returns:
        A string containing the top sentences in their original order.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) <= num_sentences:
        return text

    words = tokenize(text)
    word_freq: dict[str, float] = {}
    for w in words:
        word_freq[w] = word_freq.get(w, 0) + 1

    if not word_freq:
        return " ".join(sentences[:num_sentences])

    max_freq = max(word_freq.values())
    for w in word_freq:
        word_freq[w] /= max_freq

    scored: list[tuple[int, float]] = []
    for i, sent in enumerate(sentences):
        score = sum(word_freq.get(w, 0.0) for w in tokenize(sent))
        scored.append((i, score))

    top = sorted(scored, key=lambda x: x[1], reverse=True)[:num_sentences]
    top.sort(key=lambda x: x[0])  # Preserve original order

    logger.debug("Summarized %d sentences down to %d", len(sentences), len(top))
    return " ".join(sentences[idx] for idx, _ in top)
