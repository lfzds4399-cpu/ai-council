"""Example: should we buy this domain?

Three voters, each looking at a different angle:

- ``SeoVoter`` — domain authority and backlink profile
- ``BrandVoter`` — name length, language, trademark conflict heuristics
- ``ResaleVoter`` — comparable past sale price for similar TLDs

The proposal carries one row of domain data; the council returns whether to
acquire it within the buyer's budget.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_council import Council, Vote, function_voter  # noqa: E402


def seo_voter(proposal, context, peers):
    score = 50.0
    reasons: list[str] = []
    da = proposal.get("domain_authority", 0)
    backlinks = proposal.get("referring_domains", 0)
    if da >= 30:
        score += 25
        reasons.append(f"DA {da} ≥ 30")
    elif da >= 15:
        score += 10
    elif da == 0:
        score -= 10
        reasons.append("no DA — likely fresh registration")
    if backlinks >= 50:
        score += 15
        reasons.append(f"{backlinks} referring domains")
    return Vote(
        voter="seo",
        approve=score >= 60,
        score=min(100, max(0, score)),
        reasons=reasons,
    )


def brand_voter(proposal, context, peers):
    name = proposal["name"]
    score = 50.0
    reasons: list[str] = []
    if len(name) <= 8:
        score += 20
        reasons.append("short")
    elif len(name) > 15:
        score -= 15
        reasons.append("long")

    if name.replace("-", "").isalpha():
        score += 10
        reasons.append("letters only")
    if "-" in name or any(c.isdigit() for c in name):
        score -= 10
        reasons.append("contains hyphen or digit")

    # Hard veto on obvious trademark hits
    blocked = {"google", "apple", "amazon", "microsoft", "openai", "anthropic"}
    if any(b in name.lower() for b in blocked):
        return Vote(
            voter="brand",
            approve=False,
            score=0,
            reasons=["matches a trademarked brand"],
            veto=True,
        )
    return Vote(
        voter="brand",
        approve=score >= 55,
        score=min(100, max(0, score)),
        reasons=reasons,
    )


def resale_voter(proposal, context, peers):
    score = 50.0
    reasons: list[str] = []
    asking = float(proposal.get("asking_usd", 0))
    comp = float(context.get("comparable_median_usd", asking))
    if asking <= 0:
        return Vote(voter="resale", approve=False, score=0, reasons=["no price"])
    ratio = asking / comp if comp > 0 else 1.0
    if ratio < 0.7:
        score += 30
        reasons.append(f"price {ratio:.1%} of comparable median")
    elif ratio < 1.0:
        score += 10
    elif ratio > 1.5:
        score -= 25
        reasons.append(f"price {ratio:.1%} of comparable median (overpriced)")
    return Vote(
        voter="resale",
        approve=score >= 55,
        score=min(100, max(0, score)),
        reasons=reasons,
    )


def main() -> None:
    council = Council(
        [
            function_voter("seo", seo_voter, weight=1.0),
            function_voter("brand", brand_voter, weight=1.5),
            function_voter("resale", resale_voter, weight=1.0),
        ],
        threshold=2,
    )

    proposal = {
        "name": "saasflux.io",
        "domain_authority": 22,
        "referring_domains": 65,
        "asking_usd": 1800,
    }
    context = {"comparable_median_usd": 2400}

    decision = council.deliberate(proposal, context)
    print(f"Decision: {'BUY' if decision.approved else 'SKIP'}")
    print(f"Final score: {decision.final_score}")
    for v in decision.votes:
        verdict = "APPROVE" if v.approve else "REJECT"
        veto = " (VETO)" if v.veto else ""
        print(f"  {v.voter:>8}: {verdict}{veto} score={v.score:.1f} — {', '.join(v.reasons) or '—'}")


if __name__ == "__main__":
    main()
