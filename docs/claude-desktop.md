# Claude Desktop Setup

## Installation Steps

1. Clone the repository to a permanent location.
   ```bash
   git clone https://github.com/rajfazulhussain2008/markindex-mcp.git
   cd markindex-mcp
   ```

2. Create and activate a Python virtual environment.
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. Install requirements.
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

You must configure Claude Desktop to run the MarkIndex server using **absolute paths**.

### Windows Path Example
Edit `%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "markindex": {
      "command": "C:\\path\\to\\markindex-mcp\\venv\\Scripts\\python.exe",
      "args": ["-m", "markindex"],
      "cwd": "C:\\path\\to\\markindex-mcp"
    }
  }
}
```

### macOS/Linux Path Example
Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "markindex": {
      "command": "/absolute/path/to/markindex-mcp/venv/bin/python",
      "args": ["-m", "markindex"],
      "cwd": "/absolute/path/to/markindex-mcp"
    }
  }
}
```

## Restart Claude Desktop
Fully quit the Claude Desktop application (Cmd+Q or Alt+F4) and reopen it for the changes to take effect.

## Troubleshooting Common Mistakes
1. **Using relative paths**: Claude Desktop evaluates paths differently. Always use full, absolute paths to the Python executable and the `cwd`.
2. **Missing virtual environment**: Ensure `command` points directly to the `python` binary *inside* the `venv` so all dependencies are found.
3. **Invalid JSON**: Ensure no trailing commas in `claude_desktop_config.json`.
