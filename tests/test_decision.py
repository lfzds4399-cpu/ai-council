"""Vote / Decision dataclass tests."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_council import Decision, Vote  # noqa: E402


def test_vote_to_dict_round_trip() -> None:
    v = Vote(voter="a", approve=True, score=80, reasons=["good"], veto=False)
    d = v.to_dict()
    assert d == {
        "voter": "a",
        "approve": True,
        "score": 80,
        "reasons": ["good"],
        "veto": False,
    }


def test_decision_helpers() -> None:
    votes = [
        Vote(voter="a", approve=True, score=80),
        Vote(voter="b", approve=False, score=20, veto=True),
        Vote(voter="c", approve=True, score=70),
    ]
    d = Decision(
        approved=False,
        final_score=56.7,
        votes=votes,
        threshold_met=True,
        veto_triggered=True,
        proposal={"id": "x"},
    )
    assert d.approve_count == 2
    assert d.veto_voters == ["b"]
    serialised = d.to_dict()
    assert serialised["proposal"] == {"id": "x"}
    assert len(serialised["votes"]) == 3
    assert serialised["votes"][1]["veto"] is True


def test_decision_timestamp_iso() -> None:
    d = Decision(
        approved=True,
        final_score=80,
        votes=[Vote(voter="a", approve=True, score=80)],
        threshold_met=True,
        veto_triggered=False,
        proposal={},
    )
    # ISO-8601 with timezone, no microseconds — predictable for logs.
    assert "T" in d.timestamp
    assert d.timestamp.endswith("+00:00")
