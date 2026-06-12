# Example MCP LLM Workflow

This document illustrates how an LLM can use MarkIndex MCP tools sequentially.

1. **Ingest the file**
   ```python
   ingest_document("examples/sample_policy.md")
   # Returns doc_id: "doc_123"
   ```

2. **Search for relevant context**
   ```python
   search_sections(doc_id="doc_123", query="vehicle compensation", limit=3)
   # Matches "Vehicle Compensation" section.
   ```

3. **Read the matched section**
   ```python
   read_section(doc_id="doc_123", section_title="vehicle-compensation")
   # Returns the full text about the $0.65 per mile rate.
   ```

4. **Navigate to the next section**
   ```python
   get_adjacent_sections(doc_id="doc_123", section_title="vehicle-compensation")
   # Returns the next section ("Summary") to continue reading.
   ```

5. **Save the analysis**
   ```python
   save_to_outputs("policy_summary.md", "Employees receive $0.65/mile.")
   ```
