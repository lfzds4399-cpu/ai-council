# Contributing

Thanks for your interest. Small, focused PRs get reviewed fastest.

`ai-council` is intentionally tiny and zero-dependency at runtime. New features should preserve both properties.

## Setup

```bash
git clone https://github.com/lfzds4399-cpu/ai-council.git
cd ai-council
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Run quality gates locally

```bash
ruff check .
pytest -q
```

CI runs the same suite on Python 3.11 / 3.12 / 3.13.

## Commit conventions

- Imperative tense: `fix: handle empty council` — not `fixed` or `fixes`
- One concern per commit
- If your change is user-visible, add a line to `CHANGELOG.md` under `## [Unreleased]`

## Adding a new voter helper

`function_voter(name, fn, *, weight=1.0)` covers the common case (any callable becomes a `Voter`, with optional weight). New voter helpers belong in `ai_council/voter.py` and must:

1. Return a `Vote` (never raise on rejection — return `Vote(approve=False, ...)` instead).
2. Be deterministic given the same `(proposal, context, peers)` triple. If you need an LLM, accept a callable so tests can pass a stub.
3. Stay zero-dependency. If your voter needs an LLM SDK, ship it as `examples/` rather than as core.

## What NOT to commit

- `.env` files or API keys.
- Network calls in unit tests — use stubs.
- Examples that hard-code paid endpoints — gate them behind `if os.getenv("OPENAI_API_KEY")`.

## Reporting bugs

Open a GitHub issue with: minimal repro, expected vs actual, Python version, traceback. The smaller the repro, the faster the fix.

## Security

Don't open a public issue for vulnerabilities. See [SECURITY.md](SECURITY.md).
