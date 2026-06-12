"""Hierarchical document parser for MarkIndex MCP.

Converts raw Markdown text into a navigable tree structure by detecting
multiple header formats: standard Markdown (#), SECTION, CHAPTER, APPENDIX,
numbered (1.1, 1.2.3), Roman numerals (I., II.), and time intervals (00:00 - 02:00).
"""

import re
import difflib
from typing import Any

from markindex.logger import get_logger

logger = get_logger(__name__)

# Pre-compiled header patterns ordered by priority
_HEADER_PATTERNS = [
    ("markdown",  re.compile(r"^(#{1,6})\s+(.*)")),
    ("section",   re.compile(r"^(SECTION\s+\d+.*)", re.IGNORECASE)),
    ("chapter",   re.compile(r"^(CHAPTER\s+[A-Z0-9]+(?:\s+.*)?)", re.IGNORECASE)),
    ("appendix",  re.compile(r"^(APPENDIX\s+[A-Z](?:\s+.*)?)", re.IGNORECASE)),
    ("numbered",  re.compile(r"^(\d+\.\d+(?:\.\d+)?)\s+(.*)")),
    ("roman",     re.compile(r"^([IVXLCDM]+)\.\s+(.*)", re.IGNORECASE)),
    ("timestamp", re.compile(r"^(\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})(.*)")),
]

_FORMAT_STRIP = re.compile(r"^[\*_`#\s]+|[\*_`#\s]+$")


def parse_markdown_to_tree(markdown_text: str) -> list[dict]:
    """Parse markdown text into a hierarchical tree of sections.

    Splits the input on newlines, identifies header lines via
    ``_detect_header``, and nests them according to their depth level.
    Non-header lines are accumulated as content on the most recent node.

    Args:
        markdown_text: Raw markdown string to parse.

    Returns:
        A list of top-level section nodes.  Each node is a dict with keys
        ``level``, ``title``, ``content`` (str), and ``children`` (list).
    """
    lines = markdown_text.split("\n")
    root: dict = {"level": 0, "title": "Root", "content": [], "children": []}
    stack: list[dict] = [root]

    for line in lines:
        level, title = _detect_header(line)

        if level > 0:
            title = _FORMAT_STRIP.sub("", title).strip()
            node: dict = {
                "level": level,
                "title": title,
                "content": [],
                "children": [],
            }

            while stack and stack[-1]["level"] >= level:
                stack.pop()
            if not stack:
                stack = [root]

            stack[-1]["children"].append(node)
            stack.append(node)
        else:
            stack[-1]["content"].append(line)

    _join_content(root)
    logger.debug(
        "Parsed %d top-level sections from %d lines",
        len(root["children"]),
        len(lines),
    )
    return root["children"]


def _detect_header(line: str) -> tuple[int, str]:
    """Detect if a line is a header and return its level and title.

    The function iterates through ``_HEADER_PATTERNS`` in priority order
    and returns the first match.

    Args:
        line: A single line of text to inspect.

    Returns:
        A ``(level, title)`` tuple.  Returns ``(0, "")`` when the line
        is not recognised as any header format.
    """
    for pattern_name, pattern in _HEADER_PATTERNS:
        match = pattern.match(line)
        if not match:
            continue

        if pattern_name == "markdown":
            return len(match.group(1)), match.group(2).strip()
        elif pattern_name in ("section", "chapter", "appendix"):
            return 1, match.group(1).strip()
        elif pattern_name == "numbered":
            return len(match.group(1).split(".")), line.strip()
        elif pattern_name == "roman":
            return 2, line.strip()
        elif pattern_name == "timestamp":
            title = match.group(1).strip()
            extra = match.group(2).strip()
            return 2, f"{title} {extra}".strip() if extra else title

    return 0, ""


def _join_content(node: dict) -> None:
    """Recursively join content lines into a single string.

    Mutates *node* in-place, converting ``content`` from a list of
    strings to a single stripped string, then recurses into children.

    Args:
        node: A section node whose ``content`` is still a list of lines.
    """
    node["content"] = "\n".join(node["content"]).strip()
    for child in node["children"]:
        _join_content(child)


def section_to_markdown(node: dict) -> str:
    """Render a section node back into markdown text.

    Reconstructs a Markdown heading line from the node's level and title,
    appends the body content, and then recurses into children.

    Args:
        node: A section node from the parsed tree.

    Returns:
        Formatted markdown string including all child sections.
    """
    md = f"{'#' * node['level']} {node['title']}\n\n{node['content']}"
    if node["content"]:
        md += "\n\n"
    for child in node["children"]:
        md += section_to_markdown(child) + "\n\n"
    return md.strip()


def get_outline(tree: list[dict]) -> list[dict]:
    """Generate a hierarchical outline with character counts.

    Useful for providing a high-level map of a document without
    returning the full body text.

    Args:
        tree: Parsed section tree.

    Returns:
        Nested list of dicts with ``title``, ``size_chars``, and
        optional ``children``.
    """
    outline: list[dict] = []
    for node in tree:
        entry: dict[str, Any] = {
            "title": node["title"],
            "size_chars": len(section_to_markdown(node)),
        }
        if node["children"]:
            entry["children"] = get_outline(node["children"])
        outline.append(entry)
    return outline


def find_section(tree: list[dict], target_title: str) -> dict | None:
    """Locate a section by title using a three-phase resolution strategy.

    Resolution order:
        1. Exact case-insensitive match.
        2. Substring containment match.
        3. Fuzzy match via ``difflib.get_close_matches`` (cutoff 0.4).

    Args:
        tree: Parsed section tree.
        target_title: The title (or partial title) to search for.

    Returns:
        The matching section node, or ``None`` if no match is found.
    """
    target = target_title.lower().strip()

    # Phase 1 — exact
    def _exact(nodes: list[dict]) -> dict | None:
        for node in nodes:
            if node["title"].lower().strip() == target:
                return node
            found = _exact(node["children"])
            if found:
                return found
        return None

    # Phase 2 — substring
    def _substring(nodes: list[dict]) -> dict | None:
        for node in nodes:
            if target in node["title"].lower().strip():
                return node
            found = _substring(node["children"])
            if found:
                return found
        return None

    result = _exact(tree)
    if result:
        return result
    result = _substring(tree)
    if result:
        return result

    # Phase 3 — fuzzy
    mapping: dict[str, dict] = {}
    _collect_titles(tree, mapping)
    close = difflib.get_close_matches(
        target, list(mapping.keys()), n=1, cutoff=0.4,
    )
    if close:
        logger.debug("Fuzzy matched '%s' → '%s'", target_title, close[0])
        return mapping[close[0]]

    return None


def _collect_titles(nodes: list[dict], mapping: dict[str, dict]) -> None:
    """Recursively collect all section titles into a flat mapping.

    Args:
        nodes: List of section nodes to traverse.
        mapping: Mutable dict that accumulates lower-cased titles as keys
            and the corresponding node dicts as values.
    """
    for node in nodes:
        mapping[node["title"].lower().strip()] = node
        _collect_titles(node["children"], mapping)


def get_flat_navigation_map(tree: list[dict]) -> dict[str, dict[str, Any]]:
    """Build a flat navigation map for sequential traversal.

    Performs a depth-first walk of the tree and records each node's
    parent, previous sibling, and next sibling so that callers can
    navigate linearly through the document.

    Args:
        tree: Parsed section tree.

    Returns:
        Dict mapping each section title to its ``parent``, ``previous``,
        and ``next`` sibling titles (or ``None`` at boundaries).
    """
    flat_list: list[dict] = []
    parent_map: dict[str, str] = {}

    def _traverse(
        nodes: list[dict],
        parent_title: str | None = None,
    ) -> None:
        for node in nodes:
            flat_list.append(node)
            if parent_title:
                parent_map[node["title"]] = parent_title
            _traverse(node["children"], node["title"])

    _traverse(tree)

    nav_map: dict[str, dict[str, Any]] = {}
    for i, node in enumerate(flat_list):
        title = node["title"]
        nav_map[title] = {
            "title": title,
            "parent": parent_map.get(title),
            "previous": flat_list[i - 1]["title"] if i > 0 else None,
            "next": flat_list[i + 1]["title"] if i < len(flat_list) - 1 else None,
        }
    return nav_map
