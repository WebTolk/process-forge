#!/usr/bin/env python3
"""Deterministic isolated execution-storage scale campaign; no services or LLMs.

Requires the repository test dependencies. Fixtures and evidence remain below
an explicit absolute scratch root; this tool never selects a live PF project.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).absolute().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))


def case(root: Path, history: int, current: int) -> dict[str, object]:
    """Trace real active-only readers against a populated SQLite fixture."""
    from pf_runtime.service import RuntimeProcess

    from processforge_core.configuration import DeviceConfigurationSource
    from processforge_core.database import (
        Database,
        DatabaseFactory,
        SQLiteDriver,
        SqlStatement,
    )
    from processforge_core.executions.model import ExecutionKey
    from processforge_core.executions.sqlite_repository import (
        CURRENT_SQL,
        SQLiteExecutionRepository,
    )
    from processforge_core.runtime import metrics
    from tests.executions.test_repository import (
        cutover,
        historical,
        import_batch,
        make_harness,
    )

    project, workplace = root / "project", root / "workplace"
    data = project / ".pf/data"
    data.mkdir(parents=True)
    harness = make_harness(data, importing=True)
    # Genuine bounded import, not an all-history list or per-attempt directory scan.
    for start in range(0, history, 256):
        records = tuple(
            historical(f"terminal-{i}") for i in range(start, min(start + 256, history))
        )
        assert import_batch(harness, records) == (len(records), 0)
        harness.driver.trace.clear()
        harness.driver.visits.clear()
    cutover(harness)
    for index in range(current):
        harness.start(f"active-{index}", token=f"{index + 1:032x}")
    flow = project / ".pf"
    (flow / "process-forge.yaml").write_text(
        "project: {id: project}\n", encoding="utf-8"
    )
    (flow / "configuration.yaml").write_text(
        "database:\n  profiles:\n    project_main: {scope: project, driver: sqlite, path: data/test.sqlite3}\n",
        encoding="utf-8",
    )
    (data / "execution-storage.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project_id": "project",
                "store_id": harness.database.target.identity.store_id,
                "profile_id": "project_main",
                "target_relative_path": "data/test.sqlite3",
            }
        ),
        encoding="utf-8",
    )
    cache = workplace / "runtime/pf-runtime-host/state.json"
    cache.parent.mkdir(parents=True)
    cache.write_text(
        json.dumps({"projects": [{"project_root": str(project)}], "sessions": {}}),
        encoding="utf-8",
    )
    runtime = object.__new__(RuntimeProcess)
    runtime.workplace_root, runtime.core, runtime._project_errors = (
        workplace,
        SimpleNamespace(),
        {},
    )
    stop = Event()

    def archived_writer() -> None:
        if not history:
            return
        repository = SQLiteExecutionRepository(
            Database(SQLiteDriver(), harness.database.target), "project"
        )
        while not stop.is_set():
            record = repository.load(ExecutionKey("project", "run", "terminal-0", 1))
            assert record is not None
            repository.record_collection(
                record.key,
                "collected",
                record.payload_json,
                expected_revision=record.revision,
                generation=1,
            )

    original = Path.open
    forbidden_reads = 0

    def checked_open(path: Path, *args: Any, **kwargs: Any):
        nonlocal forbidden_reads
        if path.name in {"status.json", "heartbeat.json", "exit.json"}:
            forbidden_reads += 1
            raise AssertionError("terminal/status file read")
        return original(path, *args, **kwargs)

    harness.driver.trace.clear()
    harness.driver.visits.clear()
    tracemalloc.start()
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(archived_writer)
        try:
            with (
                patch.object(
                    DatabaseFactory, "resolve_driver", return_value=harness.driver
                ),
                patch.object(
                    DeviceConfigurationSource,
                    "default_path",
                    return_value=root / "device.yaml",
                ),
                patch.object(Path, "open", checked_open),
                patch.object(Path, "glob", side_effect=AssertionError("history glob")),
            ):
                result = metrics.shutdown_workers(workplace, runtime.core)
                count = runtime.active_worker_count([project])
        finally:
            stop.set()
        future.result()
    elapsed = time.monotonic() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    expected = current if current <= 128 else None
    assert result["counts"]["running"] == count == expected
    visits = tuple(harness.driver.visits)
    assert not any("terminal-" in str(row.values) for row in visits)
    assert sum("payload_json" in row.columns for row in visits) == 2 * min(current, 129)
    queries = tuple(harness.driver.trace)
    assert not any(
        "COUNT(" in sql.upper() or "execution_history" in sql for sql in queries
    )
    with harness.database.read() as session:
        with session.stream(
            SqlStatement("EXPLAIN QUERY PLAN " + CURRENT_SQL, ("project", 129))
        ) as rows:
            plan = [str(row["detail"]) for row in rows]
    assert any("SEARCH c USING COVERING INDEX" in detail for detail in plan)
    assert any(
        "SEARCH a USING INDEX sqlite_autoindex_execution_attempts_" in detail
        for detail in plan
    )
    return {
        "history": history,
        "current": current,
        "running": count,
        "terminal_rows_visited": 0,
        "terminal_files_read": forbidden_reads,
        "attempt_rows": sum("payload_json" in row.columns for row in visits),
        "sql_operations": len(queries),
        "peak_bytes": peak,
        "elapsed_seconds": elapsed,
        "query_plan": plan,
        "concurrent_archived_writer": history > 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch-root", type=Path, required=True)
    parser.add_argument("--histories", type=int, nargs="+", default=[0, 510, 400000])
    parser.add_argument("--currents", type=int, nargs="+", default=[0, 1, 3, 129])
    args = parser.parse_args()
    if not args.scratch_root.is_absolute() or any(
        value < 0 for value in args.histories + args.currents
    ):
        parser.error("absolute scratch root and nonnegative fixture sizes required")
    root = args.scratch_root / uuid4().hex
    root.mkdir(parents=True)
    for history in args.histories:
        for current in args.currents:
            directory = root / f"history-{history}-current-{current}"
            directory.mkdir()
            print(
                json.dumps(case(directory, history, current), sort_keys=True),
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
