# Changelog

All notable changes to MarkIndex MCP will be documented in this file.

## [2.0.0] - 2026-06-12
### Added
- JSON frontmatter tracking instead of YAML for standard interoperability.
- Added strict path security restrictions enforcing local-first architecture constraints.
- `MARKINDEX_MAX_FILE_MB` applied safely to both local file loads and URL streams.
- Extensive E2E test workflows and automated GitHub Actions CI pipeline.
- Centralized `ToolResponse` typed structure to ensure standardized tool outputs.

### Changed
- Improved URL safety checks, rejecting FTP protocols and parsing unsupported content headers safely.
- Section IDs are now deterministically stable and correctly map across duplicate document headers.
