#!/usr/bin/env python3
"""Release contributor policy, project-entry integrity and private-state exclusion."""
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
from processforge_core.maintenance.update import CORE_MANIFEST_NAME, manifest_bytes
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
        (source / "VERSION").write_text("7.4.1-dev.3+entry\n", encoding="utf-8")
        for name in ("agent-entry-contract.md", "agent-entry-contract.json", "project-agents-template.md"):
            shutil.copyfile(ROOT / "templates" / name, source / "templates" / name)
        root = source / "AGENTS.md"
        contributor_policy = b"# Repository instructions\n\nFollow CONTRIBUTING.md and submit changes through a pull request to dev.\n"
        root.write_bytes(contributor_policy.replace(b"\n", b"\r\n"))
        for name in ("CONTRIBUTING.md", "CONTRIBUTING.ru.md"):
            (source / name).write_text("# Contributing\n\nSubmit changes through a pull request to dev.\n", encoding="utf-8")
            assert name in release.RELEASE_REQUIRED_PATHS
        assert "AGENTS.md" in release.RELEASE_REQUIRED_PATHS
        assert not any(name.startswith(".pf/") for name in release.RELEASE_REQUIRED_PATHS)
        assert not (source / ".pf").exists()
        assert failures(release, source) == []
        assert release.release_required_path_exists(source, "AGENTS.md")

        root.unlink()
        assert "AGENTS.md" not in dict(release.release_source_files(source))
        assert "AGENTS.md" not in dict(validator.public_file_entries(source))
        assert not release.release_required_path_exists(source, "AGENTS.md")
        # Template validity is separate from the required contributor-policy file.
        assert failures(release, source) == []
        root.write_bytes(contributor_policy.replace(b"\n", b"\r\n"))
        assert dict(release.release_source_files(source))["AGENTS.md"] == root
        assert dict(validator.public_file_entries(source))["AGENTS.md"] == root

        metadata = source / "templates/agent-entry-contract.json"
        meta_raw = metadata.read_bytes()
        meta = json.loads(meta_raw)
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

        before_sources = release.release_source_files(source)
        before_inventory = validator.build_inventory(source)
        (source / ".pf").mkdir()
        for name in ("AGENTS.md", "process-forge.yaml", "hooks.yaml"):
            (source / ".pf" / name).write_text("private local state\n", encoding="utf-8")
        assert failures(release, source) == [], "local project state must not govern distribution checks"
        assert release.release_source_files(source) == before_sources
        assert validator.build_inventory(source) == before_inventory

        inventory = source / "checksums/processforge.sha256"
        inventory.parent.mkdir()
        inventory.write_text(validator.build_inventory(source), encoding="utf-8")
        files = release.release_source_files(source)
        version = (source / "VERSION").read_text(encoding="utf-8").strip()
        assert version != "unknown"
        owned = release.release_core_manifest(
            files, version=version, source=None, generated_at="2026-01-01T00:00:00Z"
        )
        archive_path = base / "candidate.zip"
        entries = release.write_release_zip(archive_path, files, 1767225600,
                    extra_entries=[(CORE_MANIFEST_NAME, manifest_bytes(owned))])
        extracted = base / "extracted"
        with zipfile.ZipFile(archive_path) as archive:
            assert archive.read("AGENTS.md") == contributor_policy
            assert not any(name.startswith(".pf/") for name in archive.namelist())
            for name in ("CONTRIBUTING.md", "CONTRIBUTING.ru.md"):
                assert archive.read(name) == validator.released_content(source / name)
            assert archive.read("templates/agent-entry-contract.md") == contract.raw
            for row in entries:
                assert hashlib.sha256(archive.read(row["path"])).hexdigest() == row["sha256"]
            archive.extractall(extracted)
        assert failures(release, extracted) == []
        assert not (extracted / ".pf").exists()
        assert validator.build_inventory(extracted) == inventory.read_text(encoding="utf-8")
        for row in owned["files"]:
            raw = (extracted / row["relative_path"]).read_bytes()
            assert len(raw) == row["size"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
        # Contributor-policy changes invalidate checksums, not the consumer startup contract.
        (extracted / "AGENTS.md").write_bytes(b"changed archive root\n")
        assert validator.build_inventory(extracted) != inventory.read_text(encoding="utf-8")
        assert failures(release, extracted) == []
    print("PASS: contributor policy, project-entry integrity, private-state exclusion, readonly validation, ZIP/checksum/owned-manifest parity.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
