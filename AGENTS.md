# AGENTS.md

AI-powered GitHub automation tools, shipped as reusable GitHub Actions.
MVP tool (AI PR Reviewer) is shipped and working end-to-end against real
GitHub PRs and the Gemini API.

## Stack

Python 3.11+, managed with `uv` (not pip/venv directly). Pydantic for
schemas/validation, `httpx` for all HTTP (GitHub REST API and LLM calls),
`unidiff` for diff parsing, `PyYAML` for config.

## Commands

```bash
uv sync --extra dev              # install everything, including dev deps
uv run pytest tests/ -v          # run tests
uv run ruff check src/ tests/ scripts/   # lint
uv run ai-toolkit hello          # sanity check the CLI installs/runs
uv run ai-toolkit review-pr --pr-number N   # run the reviewer locally
```

Env vars load from `.env` via `uv run --env-file .env ...` or
`export UV_ENV_FILE=.env` once per shell session. See `.env.example`.

## Testing conventions

- **Never call a real GitHub or LLM API in `pytest`.** `GitHubClient` and
  `OpenAICompatibleProvider` are built on injectable `httpx.Client` /
  `httpx.AsyncClient`, so tests use `httpx.MockTransport`. For
  orchestration logic (`reviewer.py`), use a fake `LLMProvider` (see
  `tests/test_pr_reviewer_orchestration.py::FakeProvider`) instead of
  mocking HTTP directly.
- One real, live-network check exists per provider:
  `scripts/smoke_test_provider.py`. Run manually with a real key, never
  in CI.
- Every new module needs tests before being considered done — this repo
  has built every piece (diff parser, GitHub client, providers,
  orchestration, CLI, telemetry) test-first, verifying locally before
  ever touching a real GitHub Actions run.

## Architecture

```
src/ai_toolkit/
├── core/           # GitHub client, diff parser, config loading — no LLM calls
├── providers/      # LLMProvider interface + implementations
├── tools/          # one folder per tool (pr_reviewer/, pr_description/, ...)
│   └── <tool>/prompts.py, schema.py, reviewer.py (or equivalent)
├── shared/         # errors, telemetry — used across tools and providers
└── cli.py          # argparse subcommands, one per tool
```

Adding a new tool: new folder under `tools/`, reusing `core/`,
`providers/`, `shared/` unchanged. Adding a new provider: new class
implementing `providers/base.py::LLMProvider`.

**Deliberate non-obvious rules:**
- No `providers/registry.py` until there are 2+ providers — avoid
  premature abstraction. Currently only `OpenAICompatibleProvider`
  exists (covers Gemini, Groq, OpenRouter, self-hosted Ollama/vLLM via
  `base_url` + `model` config, no per-provider classes needed for these).
- Comments should explain *why*, not restate *what* — keep docstrings to
  one line unless there's a genuinely non-obvious reason behind a
  decision.
- Telemetry (`shared/telemetry.py`) prints to stdout **and** writes
  `$GITHUB_STEP_SUMMARY` — don't rely on the Step Summary UI alone,
  since it's easy to miss.
- `action.yml` installs via `pip install "${{ github.action_path }}"`,
  not from PyPI — this package is not published, and publishing is
  intentionally deferred.

## Current scope

- **Shipped, wired into `action.yml`:** AI PR Reviewer (`review-pr`), PR
  Description Generator (`describe-pr`), Test Recommendation
  (`recommend-tests` — prose suggestions only, no code generation, no
  execution; scope decided explicitly, don't expand it without asking).
  All fully tested; `review-pr` verified on a real PR.
- **`describe-pr` is done, not being iterated on further** — the known
  PR-template limitation (see "Deferred" below) stays as-is unless
  explicitly requested.
- **Shipped, CLI-only — will not be wired into `action.yml`:** Changelog
  Generator (`generate-changelog`). It needs different inputs (`base`/
  `head` refs, no PR number) than the PR-scoped tools, and bolting that
  onto the composite action via conditional bash branching was
  considered and explicitly rejected. It's invoked directly:
  `uv run ai-toolkit generate-changelog --base <ref> --head <ref>`, or a
  consumer can write their own thin workflow step calling the published
  CLI. Do not revisit this without discussing the design first — it's a
  real architectural fork (single flexible action vs. multiple composite
  actions), not a small addition.
- **V1 locked to exactly the two above** — Commit Message Generator,
  Code Explanation, `AnthropicProvider`, a JSON artifact telemetry sink,
  and config-schema docs were considered and explicitly cut, not
  deferred.
- **Not planned:** PyPI publishing, `.agents/` directory, Agent Skills
  (`SKILL.md`) — no concrete need for these yet.
- **Deferred (not cut):** PR Description Generator doesn't detect an
  unedited GitHub PR template vs. a genuinely empty body — it only
  checks for empty/whitespace. On template-using repos it will always
  comment instead of filling in. The fix (fetch the repo's template
  file, compare against the PR body) was scoped but not built — pick up
  only if asked.

## Before making changes

Do not start implementation on your own initiative — confirm scope with
the maintainer first, even for changes that seem clearly implied by
prior discussion.
