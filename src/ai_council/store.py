"""Persistence backends for meeting records.

The council optionally hands off each :class:`Decision` to a
:class:`MeetingStore` so a downstream system (UI, audit log, replay test)
can re-load history. Default is :class:`NullMeetingStore`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, cast

from ai_council.decision import Decision


class MeetingStore(Protocol):
    """Persistence backend for council decisions."""

    def append(self, decision: Decision) -> None: ...

    def recent(self, limit: int = 20) -> list[dict[str, Any]]: ...


class NullMeetingStore:
    """No-op store. The council performs no I/O unless another store is set."""

    def append(self, decision: Decision) -> None:  # noqa: D401, ARG002
        return None

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:  # noqa: ARG002
        return []


class JsonMeetingStore:
    """Append decisions to a JSON file, keep at most ``max_entries``.

    The file is rewritten in full on each append. Suitable for low-frequency
    audit logs; swap in a database-backed store for higher write throughput.
    """

    def __init__(self, path: str | Path, *, max_entries: int = 200) -> None:
        self.path = Path(path)
        self.max_entries = max_entries

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return cast("list[dict[str, Any]]", data)

    def append(self, decision: Decision) -> None:
        entries = self._load()
        entries.append(decision.to_dict())
        entries = entries[-self.max_entries :]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._load()[-limit:]
