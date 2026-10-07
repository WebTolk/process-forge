#!/usr/bin/env python3
"""Release entry parity, explicit source ownership and fail-closed projections."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]
from processforge_core.agent_entry.contract import encoded, load_contract
from processforge_core.core_update import CORE_MANIFEST_NAME, manifest_bytes
from smoke_remediation_checksum_surface import load_release_module, load_validator


def snapshot(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def failures(release, root: Path) -> list[str]:
    before = snapshot(root)
    checks = release.release_agent_entry_checks(root)
    assert snapshot(root) == before, "release entry validation wrote files"
    rejected = [row.message for row in checks if row.level == "FAIL"]
    assert all("\nWhy:\n" in message and "\nFix:\n" in message for message in rejected)
    return [message.splitlines()[0] for message in rejected]


def main() -> int:
    release, validator = load_release_module(ROOT), load_validator(ROOT)
    contract = load_contract(ROOT)
    with tempfile.TemporaryDirectory(prefix="pf-release-entry-") as temporary:
        base = Path(temporary)
        source = base / "source"
        (source / "templates").mkdir(parents=True)
        (source / ".pf").mkdir()
        for name in ("agent-entry-contract.md", "agent-entry-contract.json", "project-agents-template.md"):
            shutil.copyfile(ROOT / "templates" / name, source / "templates" / name)
        root, hidden = source / "AGENTS.md", source / ".pf/AGENTS.md"
        root.write_bytes(contract.render())
        hidden.write_bytes(contract.render(extended=True))
        assert failures(release, source) == []
        assert release.release_required_path_exists(source, "AGENTS.md")

        root.unlink()
        assert "AGENTS.md" not in dict(release.release_source_files(source))
        assert "AGENTS.md" not in dict(validator.public_file_entries(source))
        assert not release.release_required_path_exists(source, "AGENTS.md")
        assert failures(release, source) == ["release agent entry invalid: AGENTS.md: entry_projection_unavailable"]
        # A valid canonical template and hidden projection still cannot replace the root.
        root.write_bytes(contract.render())
        assert dict(release.release_source_files(source))["AGENTS.md"] == root
        assert dict(validator.public_file_entries(source))["AGENTS.md"] == root

        for path in (root, hidden):
            original = path.read_bytes()
            for value, reason in (
                (b"Read the hidden file instead.\n", "entry_contract_missing"),
                (original.replace(b"Locate", b"LOCATE", 1), "managed_content_changed"),
                (original.replace(f"contract={contract.version}".encode(), b"contract=999.0.0", 1), "managed_version_unknown"),
                (original + contract.raw, "managed_markers_invalid"),
            ):
                path.write_bytes(value)
                assert failures(release, source) == [f"release agent entry invalid: {path.relative_to(source).as_posix()}: {reason}"]
            path.write_bytes(original.replace(b"\n", b"\r\n"))
            assert failures(release, source) == [], "canonical release LF normalization must be supported"
            path.write_bytes(original)

        metadata = source / "templates/agent-entry-contract.json"
        meta_raw = metadata.read_bytes()
        meta = json.loads(meta_raw)
        previous = contract.raw.replace(f"contract={contract.version}".encode(), b"contract=0.9.0", 1)
        older = copy.deepcopy(meta)
        older["known_blocks"].append({"version": "0.9.0", "sha256": hashlib.sha256(previous).hexdigest()})
        metadata.write_bytes(encoded(older))
        hidden.write_bytes(previous)
        assert failures(release, source) == ["release agent entry invalid: .pf/AGENTS.md: entry_contract_outdated"]
        hidden.write_bytes(contract.render(extended=True))
        metadata.write_bytes(meta_raw)
        corrupt = copy.deepcopy(meta)
        corrupt["sha256"] = "0" * 64
        metadata.write_bytes(encoded(corrupt))
        assert failures(release, source) == ["release agent entry source invalid: contract_hash_mismatch"]
        metadata.write_bytes(meta_raw)
        derived = source / "templates/project-agents-template.md"
        derived.write_bytes(b"stale template\n")
        assert failures(release, source) == ["release agent entry source invalid: derived_template_stale"]
        derived.write_bytes(contract.render(extended=True))
        assert failures(release, source) == []

        inventory = source / "checksums/processforge.sha256"
        inventory.parent.mkdir()
        inventory.write_text(validator.build_inventory(source), encoding="utf-8")
        files = release.release_source_files(source)
        owned = release.release_core_manifest(files, version=release.RELEASE_ARCHIVE_VERSION, source=None, generated_at="2026-01-01T00:00:00Z")
        archive_path = base / "candidate.zip"
        entries = release.write_release_zip(archive_path, files, 1767225600,
                    extra_entries=[(CORE_MANIFEST_NAME, manifest_bytes(owned))])
        extracted = base / "extracted"
        with zipfile.ZipFile(archive_path) as archive:
            assert archive.read("AGENTS.md") == contract.raw
            assert archive.read(".pf/AGENTS.md") == contract.render(extended=True)
            assert archive.read("templates/agent-entry-contract.md") == contract.raw
            for row in entries:
                assert hashlib.sha256(archive.read(row["path"])).hexdigest() == row["sha256"]
            archive.extractall(extracted)
        assert failures(release, extracted) == []
        assert validator.build_inventory(extracted) == inventory.read_text(encoding="utf-8")
        for row in owned["files"]:
            raw = (extracted / row["relative_path"]).read_bytes()
            assert len(raw) == row["size"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
        # Tampering with the delivered projection is detected, not hidden by template fallback.
        (extracted / "AGENTS.md").write_bytes(b"changed archive root\n")
        assert validator.build_inventory(extracted) != inventory.read_text(encoding="utf-8")
        assert failures(release, extracted)
    print("PASS: explicit root/hidden entry sources, current K guards, readonly validation, ZIP/checksum/owned-manifest parity.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
