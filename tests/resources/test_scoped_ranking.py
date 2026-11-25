from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest

from processforge_core.resources.scoped_ranking import selected_fts_page


@pytest.mark.parametrize(
    "query", ["a", "a a", "a a a", "a.b", "Café", 'a "b"', "absent"]
)
@pytest.mark.parametrize("roots", [["one"], ["one", "two"], ["one", "two", "other"]])
def test_scoped_page_matches_native_fts5(query, roots):
    records = [
        ("one", "a a a", "a a a a a café"),
        ("one", "a", "b a b café " + "z " * 129),
        ("two", "b", "a a a b CAFÉ"),
        ("one", "rare", "other " * 17000),
        ("two", "a", "b"),
        ("other", "a " * 47, "café " * 300),
        ("other", "other", "unselected"),
    ]
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute(
            "CREATE TABLE documents(id INTEGER PRIMARY KEY, resource_id, package_id, kind, relative_path, metadata, root_id)"
        )
        db.execute(
            "CREATE VIRTUAL TABLE documents_fts USING fts5(title,content,document_id UNINDEXED,resource_id UNINDEXED)"
        )
        db.execute("CREATE VIRTUAL TABLE reference USING fts5(title,content)")
        for doc, (root, title, content) in enumerate(records, 1):
            db.execute(
                "INSERT INTO documents VALUES(?,?,?,?,?,?,?)",
                (doc, root, "p", "documentation", str(doc), "{}", root),
            )
            db.execute(
                "INSERT INTO documents_fts(rowid,title,content) VALUES(?,?,?)",
                (doc, title, content),
            )
            if root in roots:
                db.execute(
                    "INSERT INTO reference(rowid,title,content) VALUES(?,?,?)",
                    (doc, title, content),
                )
        phrase = '"' + query.replace('"', '""') + '"'
        expected = db.execute(
            "SELECT reference.rowid, bm25(reference) FROM reference JOIN documents d ON d.id=reference.rowid "
            "WHERE reference MATCH ? ORDER BY bm25(reference), d.resource_id, d.relative_path, d.root_id",
            (phrase,),
        ).fetchall()
        total, rows = selected_fts_page(db, query, roots, 2, 0)
        assert total == len(expected)
        assert [(row[0], row[6]) for row in rows] == expected[:2]
        total, rows = selected_fts_page(db, query, roots, 2, 1)
        assert total == len(expected)
        assert [(row[0], row[6]) for row in rows] == expected[1:3]
