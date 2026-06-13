# MarkIndex MCP Tool Reference

This document outlines all tools available in the MarkIndex MCP server.
All tools return a standard `ToolResponse`:
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "code": null
}
```

## Ingestion Tools

### `ingest_document(filepath: str)`
Ingest a local document from the `raw/` directory or download a supported remote URL.
**Example Call:**
`ingest_document("raw/handbook.pdf")`
**Example Success Response:**
`{"success": true, "data": {"document_id": "doc-abc", "filename": "handbook.pdf", "size_chars": 12500}, "error": null, "code": null}`
**Example Error Response:**
`{"success": false, "data": null, "error": "File too large", "code": "FILE_TOO_LARGE"}`

### `ingest_text(filename: str, text: str)`
Ingest raw Markdown text directly. Limited by `MARKINDEX_MAX_TEXT_CHARS`.
**Example Call:**
`ingest_text("snippet", "# Title\nContent")`

### `ingest_youtube(video_id: str)`
Download and ingest a YouTube video's transcript.
**Example Call:**
`ingest_youtube("dQw4w9WgXcQ")`

### `ingest_directory(dir_path: str)`
Recursively scan and ingest all supported documents in a folder.
**Example Call:**
`ingest_directory("raw/policies")`

## Exploration Tools

### `get_document_outline(doc_id: str)`
Returns the hierarchical document structure and stable section IDs.
**Example Call:**
`get_document_outline("doc-abc")`

### `search_sections(doc_id: str, query: str, is_regex: bool = False, limit: int = 50)`
Search within a specific document using TF-IDF ranking.
**Example Call:**
`search_sections("doc-abc", "PTO policy")`

### `search_all_documents(query: str, is_regex: bool = False, limit: int = 10)`
Search globally across all indexed documents.
**Example Call:**
`search_all_documents("vacation days", limit=5)`

### `read_section(doc_id: str, section_title: str, start_char: int = 0, max_chars: int = null)`
Read a complete, paginated markdown section by its stable ID.
**Example Call:**
`read_section("doc-abc", "handbook-pto")`

### `get_adjacent_sections(doc_id: str, section_title: str)`
Retrieve the parent, previous, and next section siblings to enable sequential reading.
**Example Call:**
`get_adjacent_sections("doc-abc", "handbook-pto")`

### `summarize_section(doc_id: str, section_title: str, num_sentences: int = 5)`
Extractive term-frequency summary of a large section.
**Example Call:**
`summarize_section("doc-abc", "handbook-benefits")`

## Management Tools

### `list_documents()`
List all indexed documents in memory.
**Example Call:**
`list_documents()`

### `delete_document(doc_id: str)`
Purge a document from memory and delete its cached wiki file.
**Example Call:**
`delete_document("doc-abc")`

### `save_to_outputs(filename: str, content: str)`
Persist an AI-generated report locally in the `outputs/` directory.
**Example Call:**
`save_to_outputs("pto-summary.md", "# Summary...")`

### `get_server_status()`
Fetch the server version, total documents indexed, and memory footprint.
**Example Call:**
`get_server_status()`
