# Security Policy

MarkIndex MCP is designed natively as a "Local-First" tool intended for private knowledge indexing alongside LLMs running on desktop agents.

## Supported Versions
Only the latest major version (`2.x.x`) currently receives active security updates.

## Core Security Features
- **Local-First Design**: The server never actively contacts remote services other than standard HTTP endpoints requested explicitly by the user's local MCP agent via `ingest_document()`.
- **Default Directory Bounds**: By default (`MARKINDEX_ALLOW_EXTERNAL_FILES=false`), the ingestion system will strictly reject processing of files existing outside the `/raw/` operational directory using `os.path.commonpath`.
- **Max File Bounds**: Heavy media downloads or overly large arbitrary text blobs are blocked strictly via `MARKINDEX_MAX_FILE_MB` limits.

## Network Warning
**DO NOT** expose this Model Context Protocol server over a public network. This server grants the LLM read/write access to your local operating system. Only run this service on local loopback via standard MCP UI clients (e.g. Claude Desktop).

## Reporting a Vulnerability
To report a critical vulnerability, please open a private GitHub issue or contact the repository owner directly. Do not disclose vulnerabilities openly on the public issue tracker until a patch is merged.
