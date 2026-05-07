"""Example: should we publish this user post?

Three voters wired up as a moderation council:

- ``policy``    — keyword + structural rules
- ``toxicity``  — score from a hypothetical toxicity classifier
- ``context``   — user reputation + post history

The policy voter holds a hard veto on obvious red lines (CSAM, doxxing). The
others contribute a soft signal — even a 95 toxicity score can be balanced
by a high-reputation user posting in a sensitive thread, if you wire the
weights that way.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_council import Council, Vote, function_voter  # noqa: E402

# Pretend these come from a curated policy registry.
HARD_RED_LINES = ("csam", "doxxing", "sell-credentials")
SOFT_RED_FLAGS = ("scam", "spam", "buy-now")


def policy_voter(proposal, context, peers):
    text = (proposal.get("text") or "").lower()
    if any(rl in text for rl in HARD_RED_LINES):
        return Vote(
            voter="policy",
            approve=False,
            score=0,
            reasons=["hard red line keyword present"],
            veto=True,
        )
    soft_hits = [w for w in SOFT_RED_FLAGS if w in text]
    score = 80.0 - 15 * len(soft_hits)
    reasons = [f"soft flag: {w}" for w in soft_hits] or ["no policy issues"]
    return Vote(
        voter="policy",
        approve=score >= 55,
        score=max(0.0, score),
        reasons=reasons,
    )


def toxicity_voter(proposal, context, peers):
    """Reads a pre-computed classifier score from the proposal.

    Real implementations would call into a model here. We keep it injected so
    the example is offline-runnable.
    """
    tox = float(proposal.get("toxicity_score", 0.0))  # 0.0 - 1.0
    score = round(100 * (1 - tox), 1)
    if tox >= 0.85:
        return Vote(
            voter="toxicity",
            approve=False,
            score=score,
            reasons=[f"toxicity={tox:.2f} ≥ 0.85"],
        )
    if tox >= 0.5:
        return Vote(
            voter="toxicity",
            approve=False,
            score=score,
            reasons=[f"toxicity={tox:.2f}"],
        )
    return Vote(
        voter="toxicity",
        approve=True,
        score=score,
        reasons=[f"toxicity={tox:.2f}"],
    )


def context_voter(proposal, context, peers):
    reputation = float(context.get("user_reputation", 0))  # 0-1
    prior_strikes = int(context.get("user_prior_strikes", 0))
    score = 40 + 50 * reputation - 10 * prior_strikes
    score = min(100.0, max(0.0, score))
    reasons = [f"reputation={reputation:.2f}", f"prior_strikes={prior_strikes}"]
    return Vote(
        voter="context",
        approve=score >= 55,
        score=score,
        reasons=reasons,
    )


def main() -> None:
    council = Council(
        [
            function_voter("policy", policy_voter, weight=2.0),
            function_voter("toxicity", toxicity_voter),
            function_voter("context", context_voter),
        ],
        threshold=2,
    )

    post = {
        "text": "great tutorial, here is a buy-now link to my course",
        "toxicity_score": 0.18,
    }
    user_ctx = {"user_reputation": 0.62, "user_prior_strikes": 1}

    decision = council.deliberate(post, user_ctx)
    print(f"Decision: {'PUBLISH' if decision.approved else 'BLOCK'}")
    print(f"Final score: {decision.final_score}")
    for v in decision.votes:
        verdict = "APPROVE" if v.approve else "REJECT"
        veto = " (VETO)" if v.veto else ""
        print(f"  {v.voter:>9}: {verdict}{veto} score={v.score:.1f} — {', '.join(v.reasons) or '—'}")


if __name__ == "__main__":
    main()
