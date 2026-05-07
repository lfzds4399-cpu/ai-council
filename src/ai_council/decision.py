"""Vote / Decision data classes.

These are the value types passed between voters and the council. They are
plain dataclasses — no behaviour — so they serialise cleanly and can be
inspected from tests, logs, or persisted meeting records.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class Vote:
    """A single voter's verdict on a proposal.

    Attributes:
        voter:    Name of the voter that produced this vote.
        approve:  True if the voter is in favour of the proposal.
        score:    Numeric confidence in approval, conventionally 0-100. The
                  council aggregates ``score``; ``approve`` is a separate
                  binary signal so a voter can disagree with its own score
                  threshold (e.g. veto despite a high score).
        reasons:  Free-form rationales — kept for the meeting record.
        veto:     If True, the voter overrides the threshold: the proposal
                  cannot be approved regardless of how many other voters
                  support it.
    """

    voter: str
    approve: bool
    score: float
    reasons: list[str] = field(default_factory=list)
    veto: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Decision:
    """The council's aggregated outcome over one proposal."""

    approved: bool
    final_score: float
    votes: list[Vote]
    threshold_met: bool
    veto_triggered: bool
    proposal: dict[str, Any]
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
    )

    @property
    def approve_count(self) -> int:
        return sum(1 for v in self.votes if v.approve)

    @property
    def veto_voters(self) -> list[str]:
        return [v.voter for v in self.votes if v.veto]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # `votes` round-trips as list[dict] via asdict, no extra work needed.
        return d
