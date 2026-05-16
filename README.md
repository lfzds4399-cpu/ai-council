# ai-council

Run several voters on the same proposal and get back one decision plus the
raw vote log. A voter is just a function, a rules check, a model call, or a
human-review queue. No runtime dependencies in the core package.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

[Chinese README](README.zh-CN.md)

## Minimal example

```python
from ai_council import Council, Vote, function_voter


def policy_voter(proposal, context, peers):
    allowed = "blocked" not in proposal["text"].lower()
    return Vote(voter="policy", approve=allowed, score=100 if allowed else 0, veto=not allowed)


def quality_voter(proposal, context, peers):
    enough_detail = len(proposal["text"]) >= 20
    return Vote(voter="quality", approve=enough_detail, score=80 if enough_detail else 30)


council = Council(
    [
        function_voter("policy", policy_voter),
        function_voter("quality", quality_voter, weight=1.5),
    ],
    threshold=2,
)

decision = council.deliberate({"text": "Publish this reviewed changelog entry."})
print(decision.approved, decision.final_score)
```

## Concepts

| Concept | Purpose |
|---|---|
| `Voter` | Anything with `name`, `weight`, and `vote(proposal, context, peers)`. |
| `Vote` | One voter result: `approve`, `score`, `reason`, and optional `veto`. |
| `Council` | Runs voters, applies threshold, handles vetoes, and returns a `Decision`. |
| `Decision` | Aggregated result with raw votes and timestamp. |
| `MeetingStore` | Optional persistence for decisions, such as `JsonMeetingStore`. |

## Install

```bash
pip install git+https://github.com/lfzds4399-cpu/ai-council.git
```

Requires Python 3.11 or newer.

## Thresholds, weights, and vetoes

`threshold=2` means at least two voters must approve. `threshold=0.6` means at
least 60 percent of voters must approve.

`weight` affects the final score only. It does not reduce the number of
approvals required by the threshold.

`veto=True` blocks approval even when the threshold is met. Use it for hard
policy gates such as failed authentication, unsafe content, broken migrations,
or missing security review.

## Error handling

If a voter raises an exception, the default behavior records a failed vote
instead of crashing the whole council. Use `strict=True` during development when
you want exceptions to surface immediately.

```python
council = Council(voters, threshold=2, strict=True)
```

## Audit log

```python
from ai_council import Council, JsonMeetingStore

council = Council(voters, threshold=2, store=JsonMeetingStore("meetings.jsonl"))
```

Each call to `deliberate()` persists the proposal, vote details, reasons, and
timestamp, so a decision can be reviewed later.

## Examples

Runnable examples live in [`examples/`](examples):

- [`domain_valuation.py`](examples/domain_valuation.py)
- [`code_review.py`](examples/code_review.py)
- [`content_moderation.py`](examples/content_moderation.py)

```bash
python examples/domain_valuation.py
```

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
```

## When to use it

Reach for `ai-council` when more than one check has to sign off on the same
proposal and you want the per-voter log saved for review.

Skip it if a single model call or single rule is enough.

## License

[MIT](LICENSE)
