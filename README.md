# ai-github-toolkit

AI-powered GitHub automation tools, shipped as reusable GitHub Actions.

**Status: MVP.** AI PR Reviewer is functional end-to-end (diff fetch → LLM
review → comments posted back to the PR).

## Usage

Add this to a workflow triggered on `pull_request`:

```yaml
name: AI PR Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: your-org/ai-github-toolkit@v1
        with:
          api-key: ${{ secrets.AI_API_KEY }}
```

`api-key` is required — get a free key from
[Google AI Studio](https://aistudio.google.com/) for Gemini (the default
provider). `base-url` and `model-id` are optional overrides for other
OpenAI-compatible providers (Groq, OpenRouter, self-hosted Ollama/vLLM).

### Configuring review behavior

Optional `.github/pr-reviewer.yml` in your repo:

```yaml
review:
  focus: [bugs, security, performance]
  ignore_paths: ["*.generated.ts", "vendor/**"]
  max_comments: 10
  severity_threshold: medium
```

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
