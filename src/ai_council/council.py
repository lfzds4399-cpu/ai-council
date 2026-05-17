"""Council — runs voters over a proposal and aggregates a Decision.

Decision rules:
  1. Each voter emits a :class:`Vote` (approve flag, score, optional veto).
  2. ``final_score`` is the weighted mean of vote scores.
  3. The proposal is **approved** if (a) no veto fired and (b) the count of
     approving voters meets the threshold.
  4. If a vote raises an exception, it is logged and recorded as a
     ``approve=False`` vote with score 0 — one bad voter does not crash the
     council. Set ``strict=True`` on construction to re-raise instead.

Threshold semantics:
  - ``int`` (e.g. ``threshold=2``): absolute number of approvals required.
  - ``float`` in (0, 1] (e.g. ``threshold=0.6``): ratio of approvals.

The council is synchronous. Voters that need network or LLM calls should
batch, cache, or parallelise inside their own ``vote`` method.
"""
from __future__ import annotations

import logging
import math
from typing import Any

from ai_council.decision import Decision, Vote
from ai_council.store import MeetingStore, NullMeetingStore
from ai_council.voter import Voter

_log = logging.getLogger(__name__)


class Council:
    def __init__(
        self,
        voters: list[Voter],
        *,
        threshold: int | float = 0.5,
        store: MeetingStore | None = None,
        strict: bool = False,
    ) -> None:
        if not voters:
            raise ValueError("Council requires at least one voter")
        self._validate_threshold(threshold, len(voters))
        self.voters: list[Voter] = list(voters)
        self.threshold: int | float = threshold
        self.store: MeetingStore = store or NullMeetingStore()
        self.strict = strict

    @staticmethod
    def _validate_threshold(threshold: int | float, n_voters: int) -> None:
        if isinstance(threshold, bool):
            # bool is an int subclass — guard explicitly to catch typos like
            # ``threshold=True`` early.
            raise TypeError("threshold must be int or float, not bool")
        if isinstance(threshold, int):
            if threshold < 1 or threshold > n_voters:
                raise ValueError(
                    f"int threshold must be in [1, {n_voters}], got {threshold}"
                )
        elif isinstance(threshold, float):
            if not (0.0 < threshold <= 1.0):
                raise ValueError(
                    f"float threshold must be in (0, 1], got {threshold}"
                )
        else:
            raise TypeError("threshold must be int or float")

    def _absolute_threshold(self) -> int:
        n = len(self.voters)
        if isinstance(self.threshold, int):
            return self.threshold
        # float ratio → ceil so 0.5 of 3 voters means 2 approvals, not 1.
        return max(1, math.ceil(self.threshold * n))

    def deliberate(
        self,
        proposal: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Decision:
        ctx: dict[str, Any] = context or {}
        peers: dict[str, Vote] = {}

        for voter in self.voters:
            try:
                v = voter.vote(proposal, ctx, peers)
            except Exception as exc:  # noqa: BLE001
                if self.strict:
                    raise
                _log.warning(
                    "voter %s raised %s; recording as no-vote",
                    voter.name,
                    exc.__class__.__name__,
                )
                v = Vote(
                    voter=voter.name,
                    approve=False,
                    score=0.0,
                    reasons=[f"voter raised {exc.__class__.__name__}: {exc}"],
                )
            if not isinstance(v, Vote):
                raise TypeError(
                    f"voter {voter.name!r} returned {type(v).__name__}, expected Vote"
                )
            if v.voter != voter.name:
                # Voters should set their own name; patch it here rather than
                # raise, since this is an easy mistake to make.
                v = Vote(
                    voter=voter.name,
                    approve=v.approve,
                    score=v.score,
                    reasons=v.reasons,
                    veto=v.veto,
                )
            peers[voter.name] = v

        votes = list(peers.values())
        veto_triggered = any(v.veto for v in votes)
        approve_count = sum(1 for v in votes if v.approve)
        absolute_threshold = self._absolute_threshold()
        threshold_met = approve_count >= absolute_threshold
        approved = threshold_met and not veto_triggered

        weights = {v.name: max(0.0, float(v.weight)) for v in self.voters}
        total_weight = sum(weights.values()) or 1.0
        final_score = (
            sum(v.score * weights[v.voter] for v in votes) / total_weight
        )

        decision = Decision(
            approved=approved,
            final_score=round(final_score, 2),
            votes=votes,
            threshold_met=threshold_met,
            veto_triggered=veto_triggered,
            proposal=dict(proposal),
        )
        self.store.append(decision)
        return decision


def deliberate(
    voters: list[Voter],
    proposal: dict[str, Any],
    *,
    threshold: int | float = 0.5,
    context: dict[str, Any] | None = None,
) -> Decision:
    """One-shot helper for callers that don't need a long-lived Council."""
    return Council(voters, threshold=threshold).deliberate(proposal, context)
