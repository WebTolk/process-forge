"""SQLite fixture reads and deliberate failure injection for integration smokes."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.sqlite_storage import transaction


def event_path(project):
    return Path(project) / ".pf/runtime/events/events.sqlite3"


def events(project):
    return [row for _sequence, row, _error in ProcessEventJournal().records(event_path(project))]


def remove_event(project, event_id):
    journal = ProcessEventJournal()
    with journal.connection(event_path(project), writable=True) as connection:
        with transaction(connection):
            assert connection.execute("DELETE FROM admissions WHERE event_id=?", (event_id,)).rowcount == 1
            removed = connection.execute("DELETE FROM events WHERE event_id=?", (event_id,)).rowcount
            connection.execute("DELETE FROM pending_dispatch WHERE event_id=?", (event_id,))
            connection.execute("UPDATE journal_metadata SET value=CAST(value AS INTEGER)-? WHERE key='history_count'", (removed,))


def raw_records(project):
    from processforge_core.raw_hook_journal import RawHookJournal
    return [item["record"] for item in RawHookJournal().records(Path(project) / ".pf/runtime/agent-events/hooks.sqlite3")]
