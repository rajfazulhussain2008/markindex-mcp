# Release Checklist

When preparing a formal new version release (e.g. `v2.0.0`), ensure the following checklist is completed:

## 1. Version Bump
Ensure `__version__` is updated in:
- `markindex/__init__.py`
- `pyproject.toml`
- `README.md` (badges and mentions)

## 2. Update CHANGELOG
Document changes under the new version header in `CHANGELOG.md` (if applicable).

## 3. Run Verifications
Run the following commands locally to verify full repo integrity:
```bash
ruff format --check .
ruff check .
python -m pytest tests/ --cov=markindex --cov-report=term-missing --cov-fail-under=85
python -m compileall markindex/
python -m markindex
```
*All tests, format checks, and build steps must pass with 0 errors.*

## 4. Git Tag and Release
Commit the version changes, tag the release, and push to GitHub:
```bash
git add .
git commit -m "Release v2.0.0"
git tag v2.0.0
git push origin main
git push origin v2.0.0
```

## 5. GitHub Release
- Go to the GitHub repository.
- Navigate to **Releases** > **Draft a new release**.
- Select the `v2.0.0` tag.
- Add release notes from the CHANGELOG.
- Publish.
