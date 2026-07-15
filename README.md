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

### Manually testing against a real LLM provider

`pytest` never hits a real LLM API — all provider tests run against
mocked HTTP responses so they're free and deterministic. To confirm a
provider actually works end-to-end against the real service, use the
standalone script in `scripts/`.

**Environment variables** can come from a `.env` file — uv loads these
natively, no `python-dotenv` dependency needed:

```bash
cp .env.example .env
# fill in AI_API_KEY (and optionally MODEL_ID) in .env

uv run --env-file .env python scripts/smoke_test_provider.py
```

To avoid typing `--env-file .env` every time, set it once per shell
session:

```bash
export UV_ENV_FILE=.env
uv run python scripts/smoke_test_provider.py   # .env now loads automatically
uv run pytest tests/ -v                        # also applies to any uv run command
```

`.env` is gitignored — never commit real secrets. `.env.example`
documents which variables are expected and is safe to commit.
