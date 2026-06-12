# Contributing to MarkIndex MCP

Thank you for your interest in contributing to MarkIndex MCP! Here is how you can help.

## Setup

1. Fork and clone the repository.
2. Set up a virtual environment (Python 3.11+).
3. Install development dependencies:
   ```bash
   pip install -e .[dev,youtube]
   ```

## Development

We strictly enforce Ruff linting and Pytest tests.

### Running Tests
All tests must pass. We use pytest for unit and E2E testing:
```bash
python -m pytest tests/ -v
```

### Linting & Formatting
We use `ruff` to enforce standard formatting and avoid syntax issues:
```bash
ruff check .
```

### Server Execution & Compile Checks
Make sure your changes didn't break Python module execution:
```bash
python -m compileall markindex/
python -m markindex
```

## Coding Style
- Keep functions small and focused.
- All new features should include corresponding test coverage.
- Add Google-style docstrings to any public classes and methods.
- Limit line length to 100 characters where practical.
- Do not commit any generated output files or logs.

## Submitting Pull Requests
1. Create a new branch off `main`.
2. Ensure you have tested your changes.
3. Open a PR using our Pull Request template.
4. Ensure the CI actions are green.
