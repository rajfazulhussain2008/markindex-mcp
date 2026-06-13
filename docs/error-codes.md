# MarkIndex Error Codes

When a tool fails, `success` will be `false` and the `code` field will contain one of the following structured error identifiers.

| Code | Meaning | Common Fix |
|---|---|---|
| `ACCESS_DENIED` | Attempted to access a file outside `raw/` | Move file to `raw/` or set `MARKINDEX_ALLOW_EXTERNAL_FILES=true` |
| `FILE_NOT_FOUND` | File does not exist | Verify the file path |
| `FILE_TOO_LARGE` | File exceeds limit | Ensure file < `MARKINDEX_MAX_FILE_MB` |
| `TEXT_TOO_LARGE` | Raw text exceeds limit | Ensure text < `MARKINDEX_MAX_TEXT_CHARS` |
| `UNSUPPORTED_EXTENSION` | Extension not in allowlist | Convert file to `.md`, `.pdf`, `.docx`, etc. |
| `DIR_NOT_FOUND` | Directory does not exist | Ensure directory path is correct |
| `INVALID_YOUTUBE_ID` | Invalid YouTube Video ID | Provide a standard 11-char ID |
| `YOUTUBE_ERROR` | Transcript API failed | Video might lack captions or be restricted |
| `DOC_NOT_FOUND` | Document ID not in index | Check ID via `list_documents()` |
| `SECTION_NOT_FOUND` | Section ID not matched | Check ID via `get_document_outline()` |
| `OUT_OF_BOUNDS` | Pagination index too high | Ensure `start_char` < section size |
| `EMPTY_QUERY` | Search query is empty | Provide a valid search term |
| `INVALID_LIMIT` | Limit <= 0 | Provide a limit >= 1 |
| `INVALID_FILENAME` | Output filename is invalid | Avoid slashes/directories in filename |
| `PATH_TRAVERSAL` | Filename attempted traversal | Use simple filenames like `report.md` |
| `SAVE_ERROR` | Disk write failed | Check permissions on `outputs/` |
| `DELETE_ERROR` | Cache deletion failed | Check permissions on `wiki/` |
| `INGESTION_ERROR` | MarkItDown parsing failed | Ensure document is not corrupted |
