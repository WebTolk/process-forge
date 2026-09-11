#!/usr/bin/env python3
"""Keep same-name documents from distinct authorized roots searchable and fresh."""
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from processforge_core.local_resource_search import build_index, index_status, search


def main():
    with tempfile.TemporaryDirectory(prefix="pf-multiple-roots-") as raw:
        root = Path(raw)
        roots = [root / "first", root / "second"]
        for folder, text in zip(roots, ["FirstRootMarker", "SecondRootMarker"]):
            folder.mkdir()
            (folder / "same.md").write_text(text, encoding="utf-8")
        snapshot = {"snapshot": {"id": "multiple-roots"}, "local_search_resources": [{
            "id": "fixture.multiple", "kind": "knowledge", "content_roots": [str(p) for p in roots],
            "indexing": {"mode": "fulltext", "sources": [{"path": "."}, {"path": "same.md"}]},
        }]}
        assert build_index(root, snapshot)["indexed"] == 2
        assert search(root, snapshot, query="FirstRootMarker")["total"] == 1
        assert search(root, snapshot, query="SecondRootMarker")["total"] == 1
        assert index_status(root, snapshot, verify_files=True)["status"] == "fresh"
        for index, folder in enumerate(roots):
            (folder / "same.md").write_text(f"ChangedRootMarker{index}", encoding="utf-8")
            assert index_status(root, snapshot, verify_files=True)["status"] != "fresh"
            assert build_index(root, snapshot)["indexed"] == 2
            assert search(root, snapshot, query=f"ChangedRootMarker{index}")["total"] == 1
        # Python <=3.12 may report symlink loops as RuntimeError. Exercise that
        # resolution boundary portably; real symlink permission is optional.
        original = Path.resolve
        broken = roots[0] / "loop.md"
        broken.write_text("LoopMarker", encoding="utf-8")

        def resolve(path, *args, **kwargs):
            if path == broken:
                raise RuntimeError("Symlink loop")
            return original(path, *args, **kwargs)

        with patch.object(Path, "resolve", resolve):
            assert build_index(root, snapshot)["indexed"] == 2
    print("PASS: multiple roots retain documents/freshness and resolution failures are isolated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
