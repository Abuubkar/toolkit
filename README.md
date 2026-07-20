# ai-github-toolkit

AI-powered GitHub automation tools, shipped as reusable GitHub Actions.

**Status: V1+.** Four tools shipped: AI PR Reviewer, PR Description
Generator, and Test Recommendation (all available as the GitHub Action),
plus a Changelog Generator (CLI-only — see below for why).

## Usage

### AI PR Reviewer

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

### PR Description Generator

Same Action, different `tool` input. Fills in the PR body only if it's
currently empty; if any content already exists, posts the suggestion as
a comment instead of overwriting it.

**Known limitation:** if your repo uses a GitHub PR template, the body
is auto-populated with the template text the moment a PR opens — so
this tool will see a non-empty body and always comment rather than fill
in, even though nobody actually wrote anything. Detecting "body matches
the unedited template" was considered and intentionally deferred (not
implemented) — see `AGENTS.md` if picking this back up later.

```yaml
      - uses: your-org/ai-github-toolkit@v1
        with:
          tool: describe-pr
          api-key: ${{ secrets.AI_API_KEY }}
```

`api-key` is required — get a free key from
[Google AI Studio](https://aistudio.google.com/) for Gemini (the default
provider). `base-url` and `model-id` are optional overrides for other
OpenAI-compatible providers (Groq, OpenRouter, self-hosted Ollama/vLLM).

### Test Recommendation

Same Action, different `tool` input. Posts a single PR comment
suggesting what should be tested — prose descriptions only, never
generated test code, and never executed. Suggestions aren't verified to
be correct or complete; treat them as a starting point, not a coverage
guarantee.

```yaml
      - uses: your-org/ai-github-toolkit@v1
        with:
          tool: recommend-tests
          api-key: ${{ secrets.AI_API_KEY }}
```

### Changelog Generator (CLI-only)

Not wired into `action.yml` — it needs different inputs (`base`/`head`
refs, no PR number) than the PR-scoped tools above, and that's a real
architectural fork rather than a small addition. Run it directly:

```bash
uv run ai-toolkit generate-changelog --base v1.0.0 --head main
```

Or call the published CLI from your own workflow step if you want it in
CI — see `AGENTS.md` for why this is intentionally not part of the
composite action.

### Configuring review behavior

Optional `.github/pr-reviewer.yml` in your repo:

```yaml
review:
  focus: [bugs, security, performance]
  ignore_paths: ["*.generated.ts", "vendor/**"]
  max_comments: 10
  severity_threshold: medium

# Also applies to PR Description Generator and Changelog Generator:
ignore_paths: ["*.generated.ts", "vendor/**"]
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
