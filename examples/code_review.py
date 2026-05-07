"""Example: should we merge this PR?

Three voters, each focused on one quality axis:

- ``correctness`` — diff size + presence of new tests
- ``style``      — lint output, length, docstring presence
- ``readability``— commit message length, has issue link, has reviewer

Real-world voters would call out to an LLM ("rate this diff for correctness
on a 0-100 scale"). The framework cares about the Vote shape, not how it
was produced — keep the prompt + retry logic inside each voter.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_council import Council, Vote, function_voter  # noqa: E402


def correctness_voter(proposal, context, peers):
    score = 50.0
    reasons: list[str] = []
    added = int(proposal.get("lines_added", 0))
    tests_added = int(proposal.get("tests_added", 0))
    if tests_added > 0:
        score += 25
        reasons.append(f"{tests_added} new test(s)")
    elif added > 50:
        score -= 25
        reasons.append("non-trivial change without tests")
    if added > 800:
        score -= 15
        reasons.append("large diff")
    if proposal.get("touches_migrations"):
        score -= 10
        reasons.append("touches DB migrations — needs extra care")
    return Vote(
        voter="correctness",
        approve=score >= 55,
        score=min(100, max(0, score)),
        reasons=reasons,
    )


def style_voter(proposal, context, peers):
    score = 70.0
    reasons: list[str] = []
    lint_errors = int(proposal.get("lint_errors", 0))
    if lint_errors == 0:
        reasons.append("lint clean")
    elif lint_errors < 5:
        score -= 15
        reasons.append(f"{lint_errors} lint warnings")
    else:
        score -= 35
        reasons.append(f"{lint_errors} lint errors")
    if proposal.get("missing_docstrings", 0) > 3:
        score -= 10
        reasons.append("public APIs without docstrings")
    return Vote(
        voter="style",
        approve=score >= 60,
        score=min(100, max(0, score)),
        reasons=reasons,
    )


def readability_voter(proposal, context, peers):
    score = 50.0
    reasons: list[str] = []
    msg_len = len(proposal.get("commit_message", ""))
    if msg_len >= 200:
        score += 15
        reasons.append("detailed commit message")
    elif msg_len < 30:
        score -= 20
        reasons.append("commit message too short")
    if proposal.get("issue_link"):
        score += 10
        reasons.append("links a tracked issue")
    if proposal.get("reviewer_count", 0) >= 1:
        score += 15
    else:
        score -= 10
        reasons.append("no human reviewer")
    # Auto-merging without a human reviewer on a large diff is dangerous —
    # treat that as a soft veto. (Real systems might lift the veto on docs PRs
    # only, etc. — that policy lives in the voter, not the framework.)
    if proposal.get("lines_added", 0) > 200 and proposal.get("reviewer_count", 0) == 0:
        return Vote(
            voter="readability",
            approve=False,
            score=20,
            reasons=["large change without a human reviewer"],
            veto=True,
        )
    return Vote(
        voter="readability",
        approve=score >= 55,
        score=min(100, max(0, score)),
        reasons=reasons,
    )


def main() -> None:
    council = Council(
        [
            function_voter("correctness", correctness_voter, weight=1.5),
            function_voter("style", style_voter),
            function_voter("readability", readability_voter),
        ],
        threshold=2,
    )

    pr = {
        "lines_added": 120,
        "tests_added": 3,
        "lint_errors": 0,
        "missing_docstrings": 1,
        "touches_migrations": False,
        "commit_message": "feat(council): add JsonMeetingStore for audit logs.\n\n"
        "We needed a place to persist decisions for the dashboard.",
        "issue_link": "GH-42",
        "reviewer_count": 1,
    }

    decision = council.deliberate(pr)
    print(f"Decision: {'MERGE' if decision.approved else 'BLOCK'}")
    print(f"Final score: {decision.final_score}")
    for v in decision.votes:
        verdict = "APPROVE" if v.approve else "REJECT"
        veto = " (VETO)" if v.veto else ""
        print(f"  {v.voter:>12}: {verdict}{veto} score={v.score:.1f} — {', '.join(v.reasons) or '—'}")


if __name__ == "__main__":
    main()
