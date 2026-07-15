# ai-github-toolkit

AI-powered GitHub automation tools, shipped as reusable GitHub Actions.

**Status: early scaffolding.** First tool in progress: AI PR Reviewer.

Full usage docs, config reference, and provider setup will land here as the
MVP tool becomes usable.

## Development setup

Dependencies are managed with [uv](https://docs.astral.sh/uv/).

```bash
# Install uv if you don't have it
pip install --user uv

# Install all dependencies (including dev) from the lockfile
uv sync --extra dev

# Run the CLI, tests, or lint — no need to activate the venv manually
uv run ai-toolkit hello
uv run pytest tests/ -v
uv run ruff check src/ tests/

# Add a new dependency (updates pyproject.toml + uv.lock together)
uv add some-package
uv add --dev some-dev-only-package
```

`uv.lock` is committed to the repo for reproducible installs — always
commit it alongside any `pyproject.toml` dependency change.
