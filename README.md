<div align="center">

# 📄 MarkIndex MCP

### Enterprise Document Intelligence Server

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![MCP Protocol](https://img.shields.io/badge/MCP-Compatible-00B4D8?logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSIxMCIgZmlsbD0id2hpdGUiLz48L3N2Zz4=)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.0.0-brightgreen)](pyproject.toml)

**MarkIndex** is a production-ready [Model Context Protocol](https://modelcontextprotocol.io) server that empowers LLMs to accurately navigate and retrieve information from complex documents using **Page Index RAG** methodology.

Built on [Microsoft MarkItDown](https://github.com/microsoft/markitdown) for universal document conversion and a custom hierarchical section parser with TF-IDF search ranking.

</div>

---

## ✨ Features

| Capability | Description |
|---|---|
| 📥 **Universal Ingestion** | PDF, Word, Excel, PowerPoint, HTML, TXT, Markdown, URLs |
| 🎬 **YouTube Transcripts** | Auto-download and index video transcripts with time-chunking |
| 📂 **Batch Directory Scan** | Ingest all supported files from a directory in one call |
| 🌳 **Hierarchical Parsing** | Detects `#`, SECTION, CHAPTER, APPENDIX, numbered, Roman, and timestamp headers |
| 🔍 **TF-IDF Search** | Relevance-ranked full-text search with regex support and context snippets |
| 📖 **Paginated Reading** | Character-level pagination for reading large sections without overflow |
| 🧭 **Tree Navigation** | Parent, previous, next sibling traversal for sequential reading |
| 📝 **Extractive Summaries** | Term-frequency sentence scoring for quick section overviews |
| 💾 **Persistent Cache** | Markdown files with YAML frontmatter — human-readable, git-friendly |

---

## ⚙️ How It Works: The 3-Folder Secret System

MarkIndex utilizes an organized, self-updating knowledge architecture:

1. **`raw/`**: Drop your source materials here (PDFs, Word documents, HTML, etc.). The server reads these files but never alters them.
2. **`wiki/`**: The server processes the raw files and structures them into cross-linked Markdown pages (one per document). It also generates a master `index.md` file that acts as a crawlable map, allowing the LLM to efficiently fetch context without wasting tokens.
3. **`outputs/`**: This folder automatically saves the results, reports, or plans generated every time you ask the LLM to write something based on your knowledge base.

By implementing this architecture, you essentially build a self-updating, personal consultation engine tailored to your exact data and files.

---

## ⚖️ Vector RAG vs. Page Index RAG (MarkIndex)

How does our MarkIndex methodology compare to traditional Vector Database RAG?

| Feature | Vector RAG | MarkIndex RAG |
|---|:---:|:---:|
| **Context Preservation** | 4/10 | **10/10** |
| **Setup Complexity** | 3/10 | **9/10** |
| **Cost to Run** | 5/10 | **10/10** |
| **Sequential Reading** | 2/10 | **10/10** |
| **Fuzzy Semantic Match** | **9/10** | 6/10 |
| **Total Score** | 23/50 | **45/50** |

*MarkIndex excels by preserving the original document hierarchy and allowing the LLM to paginate through full, unbroken sections, rather than receiving fragmented, out-of-context vector chunks.*

### Why MarkIndex RAG is Different:

1. **Hierarchy vs. Chunks:** Traditional Vector RAG chops documents into arbitrary 500-token chunks, destroying the author's intended structure. MarkIndex parses the actual headers (`#`, `Chapter 1`, etc.) to create a navigable tree.
2. **Full Context:** When an LLM asks MarkIndex for a section, it gets the *entire* section, exactly as it was written, rather than a few stitched-together vector matches that lack surrounding context.
3. **No Expensive Embeddings:** Vector RAG requires passing every document through an embedding model (like OpenAI `text-embedding-ada-002`), which costs time and API credits. MarkIndex uses an ultra-fast, local, pure-Python TF-IDF engine for lexical search.
4. **Token Efficiency:** Vector RAG blindly dumps 5 to 10 disjointed chunks (2,500+ tokens) into the prompt, often filling the context window with irrelevant noise. MarkIndex first feeds the LLM a tiny structural map (`index.md`), and the LLM only fetches the specific, highly-relevant section it needs, drastically reducing token waste and API costs.
5. **LLM Agency:** With MarkIndex, the LLM acts like a human reader. It can read the Table of Contents, search for keywords, jump to a specific section, and then navigate to the "next" or "previous" sections if it needs more context.

---

## 🏗️ Architecture

```
markindex-mcp/
├── markindex/                       # Python package
│   ├── __init__.py                  # Version & metadata
│   ├── __main__.py                  # python -m markindex
│   ├── config.py                    # Centralized Settings dataclass
│   ├── logger.py                    # Structured logging
│   ├── exceptions.py                # Custom exception hierarchy
│   ├── server.py                    # FastMCP server & lifecycle
│   ├── core/                        # Business logic
│   │   ├── parser.py                # Hierarchical document parser
│   │   ├── search.py                # TF-IDF ranking engine
│   │   ├── summarizer.py            # Extractive summarization
│   │   └── storage.py               # Frontmatter serialization & I/O
│   └── tools/                       # MCP tool definitions
│       ├── ingest.py                # Ingestion tools
│       ├── query.py                 # Querying tools
│       ├── navigate.py              # Navigation tools
│       └── manage.py                # Management tools
├── tests/                           # Test suite
├── pyproject.toml                   # PEP 621 packaging
├── requirements.txt                 # Dependencies
├── raw/                             # [NEW] Drop your source files here
├── wiki/                            # [NEW] Auto-generated markdown & master index.md
└── outputs/                         # [NEW] Claude's generated reports and summaries
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/markindex-mcp.git
cd markindex-mcp

# Create a virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Optional: YouTube transcript support
pip install youtube-transcript-api
```

### Running the Server

```bash
# Run as a module
python -m markindex

# Or use the CLI entry point (after pip install -e .)
markindex
```

### MCP Client Configuration

Add to your MCP client config (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "markindex": {
      "command": "python",
      "args": ["-m", "markindex"],
      "cwd": "/path/to/markindex-mcp"
    }
  }
}
```

---

## 🔧 Configuration

All settings are managed via environment variables (prefix: `MARKINDEX_`):

| Variable | Default | Description |
|---|---|---|
| `MARKINDEX_RAW_DIR` | `./raw` | Source materials directory |
| `MARKINDEX_WIKI_DIR` | `./wiki` | Processed markdown & master index directory |
| `MARKINDEX_OUTPUTS_DIR` | `./outputs` | AI generated reports directory |
| `MARKINDEX_LOG_LEVEL` | `INFO` | Log verbosity: DEBUG, INFO, WARNING, ERROR |

Copy `.env.example` → `.env` and customize as needed.

---

## 📚 Tool Reference

### Ingestion Tools

| Tool | Description |
|---|---|
| `ingest_document(filepath)` | Ingest a file or URL into the index |
| `ingest_text(title, text)` | Ingest raw text / markdown directly |
| `ingest_youtube(url_or_id, interval_seconds)` | Ingest a YouTube video transcript |
| `ingest_directory(directory_path)` | Batch-ingest all supported files from a directory |

### Query Tools

| Tool | Description |
|---|---|
| `get_document_outline(doc_id)` | Get the hierarchical Table of Contents |
| `read_section(doc_id, section_title, start_char, max_chars)` | Read a section with pagination |
| `search_sections(doc_id, query, is_regex)` | TF-IDF ranked search with regex support |

### Navigation Tools

| Tool | Description |
|---|---|
| `get_adjacent_sections(doc_id, section_title)` | Get parent / previous / next sections |
| `summarize_section(doc_id, section_title, num_sentences)` | Extractive summary of a section |

### Management Tools

| Tool | Description |
|---|---|
| `list_documents()` | List all ingested documents |
| `delete_document(doc_id)` | Delete a document from index and cache |
| `save_to_outputs(filename, content)` | **[NEW]** Save AI-generated reports to the `outputs/` folder |

---

## 🧪 Testing

```bash
# Run the test suite
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=markindex --cov-report=term-missing
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

**Built with ❤️ by Rajmohamed H**

</div>
