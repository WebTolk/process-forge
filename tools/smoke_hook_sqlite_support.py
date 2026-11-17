"""Inspect fixture SQL and inject missing effects without using a Core adapter.

The public command under test owns journal admission. These independent fixture
assertions read its persisted output; they neither initialize nor adopt stores.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


def event_path(project: Path) -> Path:
    return Path(project) / ".pf/runtime/events/events.sqlite3"


def events(project: Path) -> list[Any]:
    path = event_path(project)
    if not path.is_file():
        return []
    with closing(
        sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    ) as sql:
        return [
            json.loads(row[0])
            for row in sql.execute("SELECT record FROM events ORDER BY seq")
        ]


def remove_event(project: Path, event_id: str) -> None:
    path = event_path(project)
    with closing(
        sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True)
    ) as connection:
        with connection:
            assert (
                connection.execute(
                    "DELETE FROM admissions WHERE event_id=?", (event_id,)
                ).rowcount
                == 1
            )
            removed = connection.execute(
                "DELETE FROM events WHERE event_id=?", (event_id,)
            ).rowcount
            connection.execute(
                "DELETE FROM pending_dispatch WHERE event_id=?", (event_id,)
            )
            connection.execute(
                "UPDATE journal_metadata SET value=CAST(value AS INTEGER)-? WHERE key='history_count'",
                (removed,),
            )


def raw_records(project: Path) -> list[Any]:
    path = Path(project) / ".pf/runtime/agent-events/hooks.sqlite3"
    if not path.is_file():
        return []
    with closing(
        sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    ) as sql:
        rows = sql.execute(
            "SELECT COALESCE(h.record, r.pending_record) FROM receipts r "
            "LEFT JOIN raw_events h ON h.raw_event_id=r.raw_event_id ORDER BY r.seq"
        )
        return [json.loads(row[0]) for row in rows if row[0] is not None]
