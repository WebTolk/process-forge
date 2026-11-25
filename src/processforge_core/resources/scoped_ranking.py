"""Rank a literal phrase using only the FTS5 documents selected by a snapshot."""

from __future__ import annotations

import math
import sqlite3
from typing import Any


def _token_count(column_sizes: bytes) -> int:
    """Sum the per-column SQLite varints in an FTS5 %_docsize record."""
    total = value = 0
    for byte in column_sizes:
        value = (value << 7) | (byte & 0x7F)
        if byte < 0x80:
            total += value
            value = 0
    return total


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

    # bm25() on the shared index would include other instances in its statistics.
    # FTS5 already stores each document's length and its token positions.
    db.create_function("pf_token_count", 1, _token_count, deterministic=True)
    documents, tokens = db.execute(
        "SELECT count(*), sum(pf_token_count(s.sz)) FROM documents d "
        f"JOIN documents_fts_docsize s ON s.id = d.id WHERE {selection}",
        instance_keys,
    ).fetchone()
    average_length = tokens / documents
    idf = math.log((documents - total + 0.5) / (total + 0.5))
    if idf <= 0:
        idf = 1e-6

    def rank(frequency: int, sizes: bytes) -> float:
        # FTS5 BM25 uses k1=1.2 and b=0.75 with unit weight for both columns.
        denominator = frequency + 1.2 * (
            0.25 + 0.75 * _token_count(sizes) / average_length
        )
        return -idf * ((frequency * 2.2) / denominator)

    db.create_function("pf_phrase_rank", 2, rank, deterministic=True)
    # Tokenize only the query using the same SQLite tokenizer as documents_fts.
    db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS temp.query_text USING fts5(phrase)")
    db.execute("DELETE FROM temp.query_text")
    db.execute("INSERT INTO temp.query_text VALUES (?)", (query,))
    db.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS temp.query_terms USING fts5vocab(temp,query_text,instance)"
    )
    db.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS temp.postings USING fts5vocab(main,documents_fts,instance)"
    )
    # A phrase starts at p when every query token occurs at p + its query offset
    # in the same column. Grouping by that start also counts overlapping phrases.
    rows = db.execute(
        f"WITH hits AS (SELECT d.id {matched}), "
        "occurrences AS ("
        "SELECT p.doc, p.col, p.offset - q.offset AS phrase_start "
        "FROM temp.query_terms q CROSS JOIN temp.postings p ON p.term = q.term "
        "WHERE p.doc IN (SELECT id FROM hits) AND p.offset >= q.offset "
        "GROUP BY p.doc, p.col, p.offset - q.offset "
        "HAVING count(*) = (SELECT count(*) FROM temp.query_terms)), "
        "frequencies AS (SELECT doc, count(*) AS n FROM occurrences GROUP BY doc) "
        f"SELECT {fields}, pf_phrase_rank(f.n, s.sz) AS score FROM frequencies f "
        "JOIN documents d ON d.id = f.doc JOIN documents_fts_docsize s ON s.id = d.id "
        + page,
        [*args, limit, start],
    ).fetchall()
    return total, rows
