"""Council deliberation tests — happy paths, veto, weighting, error handling."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_council import (  # noqa: E402
    Council,
    Decision,
    JsonMeetingStore,
    Vote,
    deliberate,
    function_voter,
)

_uid = 0


def _next_id() -> int:
    global _uid
    _uid += 1
    return _uid


def _yes(score: float = 80.0, *, weight: float = 1.0):
    name = f"yes-{_next_id()}"
    return function_voter(
        name,
        lambda p, c, peers: Vote(voter="ignored", approve=True, score=score),
        weight=weight,
    )


def _no(score: float = 20.0, *, weight: float = 1.0):
    name = f"no-{_next_id()}"
    return function_voter(
        name,
        lambda p, c, peers: Vote(voter="ignored", approve=False, score=score),
        weight=weight,
    )


def _veto():
    return function_voter(
        "veto",
        lambda p, c, peers: Vote(
            voter="veto", approve=False, score=10, reasons=["red flag"], veto=True
        ),
    )


# ---------- threshold / approval ----------

def test_two_of_three_approves() -> None:
    council = Council([_yes(80), _yes(70), _no(40)], threshold=2)
    decision = council.deliberate({"id": "p1"})
    assert decision.approved is True
    assert decision.threshold_met is True
    assert decision.approve_count == 2
    assert decision.final_score == pytest.approx((80 + 70 + 40) / 3, rel=1e-3)


def test_one_of_three_does_not_pass_majority() -> None:
    council = Council([_yes(70), _no(30), _no(20)], threshold=2)
    decision = council.deliberate({"id": "p1"})
    assert decision.approved is False
    assert decision.threshold_met is False
    assert decision.approve_count == 1


def test_float_threshold_rounds_up() -> None:
    """0.5 of 3 voters → ceil → 2 approvals required, not 1."""
    council = Council([_yes(70), _no(30), _no(20)], threshold=0.5)
    decision = council.deliberate({"id": "p1"})
    assert decision.approved is False  # only 1 approval, ceil(0.5*3) = 2 needed


# ---------- veto ----------

def test_veto_blocks_even_with_quorum() -> None:
    council = Council([_yes(90), _yes(85), _veto()], threshold=2)
    decision = council.deliberate({"id": "p1"})
    assert decision.threshold_met is True  # 2 approvals are there
    assert decision.veto_triggered is True
    assert decision.approved is False
    assert decision.veto_voters == ["veto"]


# ---------- weighting ----------

def test_weighting_pulls_final_score() -> None:
    """The judge has 3x weight; final score should bend toward its 30."""
    bull = _yes(80, weight=1.0)
    bear = _yes(70, weight=1.0)
    judge = _no(30, weight=3.0)
    council = Council([bull, bear, judge], threshold=2)
    decision = council.deliberate({"id": "p1"})
    expected = (80 * 1 + 70 * 1 + 30 * 3) / (1 + 1 + 3)
    assert decision.final_score == pytest.approx(expected, rel=1e-3)


# ---------- error handling ----------

def test_voter_exception_recorded_as_no_vote() -> None:
    def boom(p, c, peers):
        raise RuntimeError("LLM down")

    council = Council(
        [_yes(80), _yes(80), function_voter("flaky", boom)],
        threshold=2,
    )
    decision = council.deliberate({"id": "p1"})
    flaky_vote = next(v for v in decision.votes if v.voter == "flaky")
    assert flaky_vote.approve is False
    assert flaky_vote.score == 0.0
    assert any("RuntimeError" in r for r in flaky_vote.reasons)
    assert decision.approved is True  # the other two carry the proposal


def test_voter_exception_strict_mode_raises() -> None:
    def boom(p, c, peers):
        raise RuntimeError("LLM down")

    council = Council([function_voter("flaky", boom)], threshold=1, strict=True)
    with pytest.raises(RuntimeError, match="LLM down"):
        council.deliberate({"id": "p1"})


# ---------- voter return-type defensive checks ----------

def test_voter_returning_non_vote_raises() -> None:
    council = Council(
        [function_voter("bad", lambda p, c, peers: "not a vote")],
        threshold=1,
    )
    with pytest.raises(TypeError, match="returned str"):
        council.deliberate({"id": "p1"})


def test_voter_name_mismatch_is_normalised() -> None:
    """If a voter sets the wrong name on its own Vote, the council patches it."""
    council = Council(
        [
            function_voter(
                "real-name",
                lambda p, c, peers: Vote(voter="lying", approve=True, score=70),
            )
        ],
        threshold=1,
    )
    decision = council.deliberate({"id": "p1"})
    assert decision.votes[0].voter == "real-name"


# ---------- threshold validation ----------

@pytest.mark.parametrize(
    "bad",
    [0, 4, -1, 1.5, 0.0, True],  # noqa: FBT003
)
def test_invalid_threshold_rejected(bad) -> None:
    voters = [_yes(50), _yes(50), _yes(50)]
    with pytest.raises((ValueError, TypeError)):
        Council(voters, threshold=bad)


def test_empty_voter_list_rejected() -> None:
    with pytest.raises(ValueError, match="at least one voter"):
        Council([], threshold=1)


# ---------- store integration ----------

def test_json_store_appends_and_caps(tmp_path: Path) -> None:
    store = JsonMeetingStore(tmp_path / "log.json", max_entries=2)
    council = Council([_yes(80)], threshold=1, store=store)
    council.deliberate({"id": "p1"})
    council.deliberate({"id": "p2"})
    council.deliberate({"id": "p3"})
    saved = json.loads((tmp_path / "log.json").read_text(encoding="utf-8"))
    assert len(saved) == 2
    assert [d["proposal"]["id"] for d in saved] == ["p2", "p3"]


# ---------- one-shot deliberate() helper ----------

def test_module_level_deliberate() -> None:
    decision: Decision = deliberate(
        [_yes(70), _yes(80)], {"id": "p1"}, threshold=2
    )
    assert decision.approved is True
    assert isinstance(decision, Decision)
