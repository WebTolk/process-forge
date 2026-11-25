"""Rank a literal phrase using only the FTS5 documents selected by a snapshot."""

from __future__ import annotations

import math
import sqlite3
from collections.abc import Iterator
from typing import Any

# An exact binary weight keeps even the largest SQLite document away from
# BM25's saturation limit when reading its integer phrase frequency.
_FREQUENCY_WEIGHT = 2.0**-32


def _sizes(record: bytes) -> Iterator[int]:
    """Read the FTS5 varints holding row counts or per-column token counts."""
    value = 0
    for byte in record:
        value = (value << 7) | (byte & 0x7F)
        if byte < 0x80:
            yield value
            value = 0


def _token_count(record: bytes) -> int:
    return sum(_sizes(record))


def _idf(documents: int, matches: int) -> float:
    if not 0 < matches <= documents:
        raise sqlite3.DatabaseError("invalid FTS5 document count")
    value = math.log((documents - matches + 0.5) / (matches + 0.5))
    return value if value > 0 else 1e-6


def _length_factor(length: int, average: float) -> float:
    return 1.2 * (0.25 + 0.75 * length / average)


def _index_sizes(db: sqlite3.Connection) -> tuple[int, int]:
    # FTS5 publishes its averages record at commit. Read current per-document
    # sizes instead when this connection has its own uncommitted changes.
    if db.in_transaction and db.total_changes:
        return db.execute(
            "SELECT count(*), sum(pf_token_count(sz)) FROM documents_fts_docsize"
        ).fetchone()
    row = db.execute("SELECT block FROM documents_fts_data WHERE id=1").fetchone()
    if row is None or not isinstance(row[0], bytes):
        raise sqlite3.DatabaseError("missing FTS5 averages record")
    counts = _sizes(row[0])
    return next(counts, 0), sum(counts)


def selected_fts_page(
    db: sqlite3.Connection, query: str, instance_keys: list[str], limit: int, start: int
) -> tuple[int, list[Any]]:
    phrase = '"' + query.replace('"', '""') + '"'
    marks = ",".join("?" for _ in instance_keys)
    selection = f"d.root_id IN ({marks})"
    matched = (
        "FROM documents_fts JOIN documents d ON d.id = documents_fts.rowid "
        f"WHERE documents_fts MATCH ? AND {selection}"
    )
    args = [phrase, *instance_keys]
    total = db.execute(f"SELECT count(*) {matched}", args).fetchone()[0]
    if start >= total:
        return total, []

    fields = "d.id, d.resource_id, d.package_id, d.kind, d.relative_path, d.metadata"
    page = "ORDER BY score, d.resource_id, d.relative_path, d.root_id LIMIT ? OFFSET ?"
    if not db.execute(
        f"SELECT 1 FROM documents d WHERE NOT ({selection}) LIMIT 1", instance_keys
    ).fetchone():
        rows = db.execute(
            f"SELECT {fields}, bm25(documents_fts) AS score {matched} {page}",
            [*args, limit, start],
        ).fetchall()
        return total, rows

    db.create_function("pf_token_count", 1, _token_count, deterministic=True)
    documents, tokens = db.execute(
        "SELECT count(*), sum(pf_token_count(s.sz)) FROM documents d "
        f"JOIN documents_fts_docsize s ON s.id = d.id WHERE {selection}",
        instance_keys,
    ).fetchone()
    all_documents, all_tokens = _index_sizes(db)
    if not tokens or not all_tokens:
        raise sqlite3.DatabaseError("missing FTS5 token counts")
    all_hits = db.execute(
        "SELECT count(*) FROM documents_fts WHERE documents_fts MATCH ?", (phrase,)
    ).fetchone()[0]
    global_idf = _idf(all_documents, all_hits)
    scoped_idf = _idf(documents, total)
    global_average = all_tokens / all_documents
    scoped_average = tokens / documents

    def scoped_rank(native_score: float, sizes: bytes) -> float:
        length = _token_count(sizes)
        # Native FTS5 counted exact phrase hits, including overlaps across
        # both indexed columns. Invert r = wf / (wf + K) to recover that count.
        ratio = -native_score / (2.2 * global_idf)
        weighted_hits = _length_factor(length, global_average) * ratio / (1.0 - ratio)
        hits = round(weighted_hits / _FREQUENCY_WEIGHT)
        return -scoped_idf * (
            (hits * 2.2) / (hits + _length_factor(length, scoped_average))
        )

    db.create_function("pf_scoped_rank", 2, scoped_rank, deterministic=True)
    rows = db.execute(
        f"SELECT {fields}, pf_scoped_rank(bm25(documents_fts, ?, ?), "
        f"(SELECT sz FROM documents_fts_docsize WHERE id=d.id)) AS score {matched} {page}",
        [_FREQUENCY_WEIGHT, _FREQUENCY_WEIGHT, *args, limit, start],
    ).fetchall()
    return total, rows
