"""Voter protocol + function_voter helper tests."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_council import Vote, Voter, function_voter  # noqa: E402


def test_function_voter_satisfies_protocol() -> None:
    v = function_voter(
        "x",
        lambda p, c, peers: Vote(voter="x", approve=True, score=50),
        weight=2.0,
    )
    assert isinstance(v, Voter)
    assert v.name == "x"
    assert v.weight == 2.0


def test_function_voter_invokes_underlying_callable() -> None:
    seen = []

    def fn(proposal, context, peers):
        seen.append((proposal, context, peers))
        return Vote(voter="x", approve=True, score=42)

    v = function_voter("x", fn)
    out = v.vote({"id": "p"}, {"key": 1}, {})
    assert out.score == 42
    assert seen == [({"id": "p"}, {"key": 1}, {})]


def test_class_based_voter_satisfies_protocol() -> None:
    """A simple class with name+weight+vote() also passes the protocol check."""

    class StaticVoter:
        name = "static"
        weight = 1.5

        def vote(self, proposal, context, peers):
            return Vote(voter="static", approve=False, score=10)

    assert isinstance(StaticVoter(), Voter)
