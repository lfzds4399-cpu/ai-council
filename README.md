# ai-council

> Multi-voter consensus framework for LLM and heuristic decisions — composable Voters, weighted votes, optional veto, persistent meeting log.

A small, dependency-free Python library for combining several "voters" (LLM calls, regex checks, classifiers, human approvers) into a single auditable decision. MIT, Python 3.11+, zero runtime dependencies.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Status](https://img.shields.io/badge/status-beta-orange)

[中文 README](README.zh-CN.md)

![ai-council demo (animated illustration)](./docs/ai-council-demo.gif)

## Minimal example

```python
from ai_council import Council, Vote, function_voter

def gpt4_voter(p, ctx, peers):    return Vote("gpt4",   approve=p["safe_gpt4"],   score=90)
def claude_voter(p, ctx, peers):  return Vote("claude", approve=p["safe_claude"], score=85)
def regex_voter(p, ctx, peers):
    bad = "kill" in p["text"].lower()
    return Vote("regex", approve=not bad, score=0 if bad else 100, veto=bad)  # hard red line

council = Council([function_voter("gpt4", gpt4_voter),
                   function_voter("claude", claude_voter),
                   function_voter("regex", regex_voter)], threshold=2)
decision = council.deliberate({"text": "...", "safe_gpt4": True, "safe_claude": True})
print(decision.approved, decision.final_score)  # True 91.67
```

## Overview

A `Council` holds a list of `Voter` objects and an approval threshold. Calling `deliberate(proposal)` runs every voter, aggregates the result, and returns a `Decision`.

A `Voter` is any object with a `name`, a `weight`, and a `vote(proposal, context, peers)` method. The body of `vote` can call an LLM, run a regex, hit a database, or ask a human queue — the framework only cares about the `Vote` returned.

The library separates four concerns that are usually tangled together: what is being decided, who votes, how votes combine (threshold / weights / veto), and where the audit log lives.

## Install

```bash
pip install ai-council              # once on PyPI
# or for now:
pip install git+https://github.com/lfzds4399-cpu/ai-council.git
```

Requires Python 3.11+. Zero runtime dependencies.

## 60-second example

```python
from ai_council import Council, Vote, function_voter

def cheap_voter(proposal, context, peers):
    cheap = proposal["price_usd"] < 100
    return Vote(voter="cheap", approve=cheap, score=80 if cheap else 20)

def reviewed_voter(proposal, context, peers):
    rated = proposal.get("rating", 0) >= 4.5
    return Vote(voter="reviewed", approve=rated, score=85 if rated else 30)

def stocked_voter(proposal, context, peers):
    in_stock = proposal.get("stock", 0) > 0
    return Vote(voter="stocked", approve=in_stock, score=90 if in_stock else 0,
                veto=not in_stock)  # out of stock → hard veto

council = Council(
    [
        function_voter("cheap", cheap_voter),
        function_voter("reviewed", reviewed_voter),
        function_voter("stocked", stocked_voter),
    ],
    threshold=2,                    # 2-of-3 must approve
)

decision = council.deliberate({"price_usd": 79, "rating": 4.7, "stock": 12})
print(decision.approved, decision.final_score)
# True 85.0
```

### LLM voter — same shape

Any object with `name`, `weight`, and a `vote(...)` method satisfies the `Voter` protocol — no inheritance needed. Drop your LLM client in directly:

```python
class ClaudeVoter:
    name = "claude"
    weight = 1.5

    def __init__(self, client): self.client = client

    def vote(self, proposal, context, peers):
        reply = self.client.messages.create(
            model="claude-sonnet-4-5",
            messages=[{"role": "user", "content": f"Approve this? {proposal}"}],
        )
        approve = "yes" in reply.content[0].text.lower()
        return Vote(voter="claude", approve=approve, score=90 if approve else 10)
```

The council does not care whether the voter is calling Anthropic, OpenAI, a SymPy verifier, or a sentiment classifier.

## Concepts

| Concept       | What it is                                                                 |
|---------------|----------------------------------------------------------------------------|
| `Voter`       | Anything with `name`, `weight`, and a `vote(proposal, context, peers)` method |
| `Vote`        | One voter's verdict: `approve` flag, `score` (0-100), reasons, optional `veto` |
| `Council`     | Holds a list of voters and the threshold; runs `deliberate(proposal)`      |
| `Decision`    | Aggregated outcome: `approved`, `final_score`, raw votes, timestamp        |
| `MeetingStore`| Optional persistence (`JsonMeetingStore` ships, write your own for DB)     |

### Threshold

- `threshold=2` — at least 2 voters must approve (absolute count)
- `threshold=0.6` — at least 60% (rounded up) must approve (ratio)

### Veto

Any voter can return `Vote(..., veto=True)`. A veto blocks approval **even if** the threshold is met. Use this for hard policy red lines (CSAM, unauthenticated payment, broken migration) where no consensus should override.

### Weighted score

`final_score` is the **weighted mean** of vote scores (the threshold check is unweighted — it's about how many voters approve). Boost a senior voter's influence with `weight=2.0` without giving them an outright veto.

### Defensive voter handling

If a voter raises an exception, by default it is logged and recorded as a `score=0, approve=False` vote — one flaky LLM call should not crash the council. Pass `strict=True` to re-raise instead.

```python
council = Council(voters, threshold=2, strict=True)  # fail loudly in dev
```

### Audit log

```python
from ai_council import JsonMeetingStore
council = Council(voters, threshold=2, store=JsonMeetingStore("meetings.jsonl"))
```

Every `deliberate()` call now persists the full `Decision` — proposal, votes, reasons, timestamp — so you can answer "why did we approve that PR / publish that post / buy that domain on 2025-04-12" months later.

## Examples

Three runnable examples in [`examples/`](examples) — each one wires up three voters for a different decision:

- [`domain_valuation.py`](examples/domain_valuation.py) — should we buy this domain? (SEO + brand + resale comp)
- [`code_review.py`](examples/code_review.py) — should we merge this PR? (correctness + style + readability)
- [`content_moderation.py`](examples/content_moderation.py) — should we publish this post? (policy + toxicity + reputation)

```bash
python examples/domain_valuation.py
```

## Where it fits

Good fits:

- **Multi-LLM ensembles** where you want each model's vote tracked + auditable (GPT + Claude + Gemini deciding together)
- **Agent routing / tool-call gating** — multiple critics vote before an agent takes an irreversible action
- **Moderation / approval flows** with a mix of model and rule-based gates
- **Code-review bots** where correctness, style, and security each get a voter
- **Decision logs** where you need to explain why a proposal passed or failed
- **Sensitive automation** where a single point of failure is unacceptable

Not a fit:

- One-call LLM judgements (just call the model)
- Reinforcement-learning style outcomes (no reward propagation here)
- Markets or auctions (use a price-clearing mechanism, not voting)

## Status

**Beta** — API surface is small and tested, but minor versions may still tweak names. Pin `ai-council==0.1.*` if you build on top.

## Contributing

Issues and PRs welcome. See pinned `help wanted` issues for low-effort first contributions: a vendored LLM-voter helper, additional `MeetingStore` backends (SQLite, Postgres), or a new domain example.

## License

[MIT](LICENSE)
