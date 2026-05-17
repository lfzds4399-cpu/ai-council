"""Voter protocol + helpers.

A voter is anything with a ``name``, a ``weight``, and a ``vote(...)`` method.
Duck typing via :class:`Voter` lets adapters wrap an LLM call, a regex check,
or a SQL query without subclassing.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ai_council.decision import Vote

# A pure-function voter signature. ``peers`` carries the votes already cast in
# this round, keyed by voter name — useful for an aggregator/judge role.
VoterFn = Callable[[dict[str, Any], dict[str, Any], dict[str, Vote]], Vote]


@runtime_checkable
class Voter(Protocol):
    """Anything that can emit a Vote on a proposal.

    Implementations are typically a small dataclass holding the model client,
    threshold, or prompt template the voter needs. Marked runtime-checkable
    so the council can validate the input list with ``isinstance``.
    """

    name: str
    weight: float

    def vote(
        self,
        proposal: dict[str, Any],
        context: dict[str, Any],
        peers: dict[str, Vote],
    ) -> Vote: ...


@dataclass
class _FunctionVoter:
    """Adapter that turns a plain function into a Voter."""

    name: str
    fn: VoterFn
    weight: float = 1.0

    def vote(
        self,
        proposal: dict[str, Any],
        context: dict[str, Any],
        peers: dict[str, Vote],
    ) -> Vote:
        return self.fn(proposal, context, peers)


def function_voter(name: str, fn: VoterFn, *, weight: float = 1.0) -> Voter:
    """Wrap a plain function as a Voter.

    Useful for quick rule-based voters or test fixtures::

        def yes_if_cheap(proposal, context, peers):
            cheap = proposal.get("price_usd", 0) < 100
            return Vote(voter="cheap", approve=cheap, score=80 if cheap else 20)

        v = function_voter("cheap", yes_if_cheap)
    """
    return _FunctionVoter(name=name, fn=fn, weight=weight)
