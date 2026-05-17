"""ai-council — multi-voter consensus framework for LLM / heuristic decisions.

Core surface:

    from ai_council import Council, Voter, Vote, Decision, deliberate

    voters = [v1, v2, v3]                     # any object satisfying Voter protocol
    council = Council(voters, threshold=2)    # 2-of-3 approve
    decision = council.deliberate(proposal)
    if decision.approved:
        ...

A ``Voter`` is anything with a ``name`` and a ``vote(proposal, context, peers)``
method returning a ``Vote``. Internals are unconstrained — rule-based,
LLM-backed, or numeric.
"""
from __future__ import annotations

from ai_council._version import __version__
from ai_council.council import Council, deliberate
from ai_council.decision import Decision, Vote
from ai_council.store import JsonMeetingStore, MeetingStore, NullMeetingStore
from ai_council.voter import Voter, VoterFn, function_voter

__all__ = [
    "__version__",
    "Council",
    "Decision",
    "JsonMeetingStore",
    "MeetingStore",
    "NullMeetingStore",
    "Vote",
    "Voter",
    "VoterFn",
    "deliberate",
    "function_voter",
]
