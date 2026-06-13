# MarkIndex Architecture

## Why No Vector DB is Required?
MarkIndex takes a "Local-First Page Index RAG" approach instead of "Vector Chunk RAG". 
- Instead of blind 500-token chunks and black-box embedding vectors, MarkIndex uses strict hierarchical parsing based on semantic document boundaries (`#`, `Chapter 1`, etc.).
- It gives the LLM a clean "Table of Contents" and allows the LLM to paginate and navigate naturally. 
- Fast TF-IDF provides high-quality keyword and regex matching without the cost, complexity, or network latency of embeddings.

## The 3-Folder Architecture
- `raw/`: Untouched user documents.
- `wiki/`: Persistent markdown cache mapping the parsed structure with JSON frontmatter.
- `outputs/`: Safe sandbox for AI-generated reports.

## Parser Flow
1. **Ingest**: File passes through Microsoft MarkItDown for universal text extraction.
2. **Detection**: Header patterns (`markdown`, `section`, `chapter`, `numbered`, `timestamp`) are prioritized and matched.
3. **Tree**: Content is structured into a `SectionNode` tree with deterministic `path` strings.
4. **Stable IDs**: Duplicate paths receive numerical suffixes (e.g. `summary-2`) for stable traversal.

## Storage Format
Each ingested document is saved to `wiki/` as a markdown file.
It contains a JSON Frontmatter block (`---` bounded) representing `DocumentMetadata`, followed by the full markdown body. This enables instant cache reloads without re-parsing files.

## Search Flow
1. Query strings are tokenized and stopwords are removed.
2. Term-frequency is calculated against all section strings.
3. Hits are boosted if the query term appears in the section title or as an exact phrase.
4. Snippets are extracted by sliding window to provide LLM context.

## Security Model
- **Path Isolation**: The `raw/` and `outputs/` directories enforce strict `os.path.commonpath()` checks against Path Traversal vulnerabilities.
- **Configurable External Access**: `MARKINDEX_ALLOW_EXTERNAL_FILES=false` completely denies access outside `raw/`.
- **Limits**: Configurable maximum file size for downloads (`MARKINDEX_MAX_FILE_MB`) and text ingestion (`MARKINDEX_MAX_TEXT_CHARS`).

## ToolResponse Standard
All MarkIndex MCP tools return a strictly typed `ToolResponse` TypedDict:
```python
class ToolResponse(TypedDict):
    success: bool
    data: Any | None
    error: str | None
    code: str | None
```
This guarantees that MCP clients and the LLM always receive predictable JSON geometry, even when errors occur.
