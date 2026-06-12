"""TF-IDF lexical search engine for MarkIndex MCP.

Provides relevance-ranked full-text search across document section trees
using a pure-Python TF-IDF implementation with optional regex support.
"""

import math
import re
from typing import Any

from markindex.logger import get_logger

logger = get_logger(__name__)


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric words.

    Args:
        text: Input text to tokenize.

    Returns:
        List of lowercase word tokens.
    """
    return re.findall(r"\b\w+\b", text.lower())


def get_ngrams(tokens: list[str], n: int) -> list[str]:
    """Generate n-grams from a list of tokens."""
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]


def rank_sections_tfidf(
    tree: list[dict],
    query: str,
    is_regex: bool = False,
) -> list[dict]:
    """Search and rank sections using TF-IDF relevance scoring.

    Args:
        tree: Parsed document section tree.
        query: Search query string.
        is_regex: If True, interpret query as a regular expression.

    Returns:
        List of matching sections sorted by relevance score (descending).
    """
    all_nodes: list[tuple[dict, list[str]]] = []

    def _flatten(nodes: list[dict], path: list[str]) -> None:
        for node in nodes:
            node_path = path + [node["title"]]
            all_nodes.append((node, node_path))
            _flatten(node["children"], node_path)

    _flatten(tree, [])

    # --- Match Filtering ---
    query_lower = query.lower().strip()
    query_unigrams_pre = tokenize(query) if not is_regex else []
    filtered: list[tuple[dict, list[str], bool, bool]] = []
    rx = None

    if is_regex:
        try:
            rx = re.compile(query, re.IGNORECASE)
        except re.error:
            rx = re.compile(re.escape(query), re.IGNORECASE)

    for node, path in all_nodes:
        if is_regex:
            t_match = bool(rx.search(node["title"])) if rx else False
            c_match = bool(rx.search(node["content"])) if rx else False
        else:
            title_lower = node["title"].lower()
            content_lower = node["content"].lower()
            
            # Match if EXACT phrase is present
            t_match = query_lower in title_lower
            c_match = query_lower in content_lower
            
            # OR Match if ANY token is present
            if not (t_match or c_match):
                for term in query_unigrams_pre:
                    if term in title_lower:
                        t_match = True
                    if term in content_lower:
                        c_match = True
        
        if t_match or c_match:
            filtered.append((node, path, t_match, c_match))

    if not filtered:
        return []

    # --- Advanced N-Gram TF-IDF ---
    query_unigrams = tokenize(query) if not is_regex else [query_lower]
    query_bigrams = get_ngrams(query_unigrams, 2) if not is_regex else []
    query_terms = list(set(query_unigrams + query_bigrams))

    if not query_terms:
        query_terms = [query_lower]

    corpus_unigrams = []
    corpus_bigrams = []
    filtered_indices = []
    for i, (node, _) in enumerate(all_nodes):
        unigrams = tokenize(f"{node['title']} {node['content']}")
        corpus_unigrams.append(unigrams)
        corpus_bigrams.append(get_ngrams(unigrams, 2))

    total_docs = len(all_nodes)
    df = {}
    for term in query_terms:
        count = 0
        for u, b in zip(corpus_unigrams, corpus_bigrams):
            if " " in term:
                if term in b: count += 1
            else:
                if term in u: count += 1
        df[term] = count

    idf = {term: math.log((total_docs + 1) / (df.get(term, 0) + 1)) + 1 for term in query_terms}

    results: list[dict] = []
    for node, path, title_matched, content_matched in filtered:
        u = tokenize(f"{node['title']} {node['content']}")
        b = get_ngrams(u, 2)
        score = 5.0 if title_matched else 0.0
        
        for term in query_terms:
            tf = b.count(term) if " " in term else u.count(term)
            if tf > 0:
                # Give higher weight to bigram matches
                weight = 2.5 if " " in term else 1.0
                score += tf * idf[term] * weight

        snippets = _extract_snippets(node["content"], query_lower, rx, content_matched)

        results.append({
            "section_title": node["title"],
            "section_id": node.get("id"),
            "path": " > ".join(path),
            "title_matched": title_matched,
            "snippets": snippets,
            "score": round(score, 4),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    logger.debug("Search '%s' returned %d results", query, len(results))
    return results


def _extract_snippets(
    content: str,
    query_lower: str,
    rx: re.Pattern | None,
    content_matched: bool,
    max_snippets: int = 3,
    context_chars: int = 80,
) -> list[str]:
    """Extract context snippets around query matches."""
    if not content_matched:
        return []

    indices: list[tuple[int, int]] = []
    if rx:
        for m in rx.finditer(content):
            indices.append((m.start(), m.end()))
    else:
        content_lower = content.lower()
        start_idx = 0
        while True:
            idx = content_lower.find(query_lower, start_idx)
            if idx == -1:
                break
            indices.append((idx, idx + len(query_lower)))
            start_idx = idx + len(query_lower)

    snippets: list[str] = []
    for start, end in indices[:max_snippets]:
        s = max(0, start - context_chars)
        e = min(len(content), end + context_chars)
        snippet = content[s:e].replace("\n", " ")
        if s > 0:
            snippet = "..." + snippet
        if e < len(content):
            snippet += "..."
        snippets.append(snippet)

    return snippets
