#!/usr/bin/env python3
"""Shared helpers for deterministic evolve smoke tests."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "bin" / "pf.py"


def run_pf(*args: str, cwd: Path | None = None, expect: int = 0, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(PF), *args],
        cwd=str(cwd or ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{result.stdout}")
    return result


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def init_project(project: Path, workplace: Path) -> None:
    project.mkdir(parents=True, exist_ok=True)
    (project / "README.md").write_text("# Evolve smoke project\n", encoding="utf-8")
    run_pf("workplace-init", "--workplace", str(workplace), "--apply")
    run_pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")


def candidate_data(candidate_id: str = "kc-docs-example-rule") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "processforge.knowledge_candidate",
        "id": candidate_id,
        "source_context": {
            "platform_stack": ["platform.example-child"],
            "knowledge_stack": ["docs.example"],
            "project_type": "example-software-project",
            "extension_type": "example-extension",
            "extension_group": "example-group",
            "package_context": {"package_id": "docs.example", "package_type": "knowledge_package"},
            "process_id": "process-authoring",
            "run_id": "run-example",
            "task_id": "task-example",
            "context_snapshot_id": "snapshot-example",
        },
        "target": {"type": "knowledge_package", "id": "docs.example", "target_path": None, "target_section": None},
        "applicability": {
            "scope": "platform",
            "applies_to": {
                "platforms": ["platform.example-child"],
                "platform_families": ["platform.example-family"],
                "knowledge_packages": ["docs.example"],
                "project_types": ["example-software-project"],
                "extension_types": ["example-extension"],
                "extension_groups": ["example-group"],
                "versions": {"platform.example-child": ">=1.0.0"},
            },
            "not_applies_to": {"platforms": ["platform.example-other"], "project_types": [], "extension_types": []},
            "conditions": ["Observed in a reusable example project context."],
            "inheritance": {
                "observed_on": ["platform.example-child"],
                "parent_platforms": ["platform.example-parent"],
                "child_platforms": [],
                "inherited_from_parent": False,
                "safe_for_parent": False,
            },
        },
        "generalization": {
            "level": "narrow_observation",
            "can_be_promoted_to": ["platform_rule"],
            "promotion_requires": ["Evidence from at least one additional project."],
            "confidence_for_promotion": "low",
        },
        "routing": {"recommended_destination": {"type": "knowledge_package", "id": "docs.example"}, "alternative_destinations": []},
        "applicability_confidence": {
            "applies_to_confidence": "observed",
            "not_applies_to_confidence": "hypothesis",
            "evidence_count": 1,
            "evidence_diversity": {"projects": 1, "platforms": 1, "versions": 1},
        },
        "category": "resource",
        "summary": "Document reusable evolve queue behavior.",
        "rationale": "The same file-first learning queue applies across processes.",
        "statement": {"details": "A reusable process observation needs explicit source, target, and applicability."},
        "suggested_change": {"proposed_text": "Keep candidates local until reviewed export."},
        "payload": {"recommendation": "Keep candidates local until reviewed export."},
        "evidence": {"files": ["relative/path.md"], "notes": ["sanitized example evidence"]},
        "sensitivity": "internal",
        "privacy": {"sanitized": True},
        "status": {"local": "proposed", "hub": None, "curation": "unreviewed", "release": "not_included"},
        "promotion": {"status": "not_requested", "target": None, "blockers": []},
        "review": {"required": False, "status": "unreviewed", "future_policy_ref": None},
        "curation": {"status": "unreviewed", "assigned_to": None},
        "release": {"included_in": None},
    }


def write_candidate(path: Path, candidate_id: str = "kc-docs-example-rule") -> Path:
    write_yaml(path, candidate_data(candidate_id))
    return path


def write_installed_subject(workplace: Path, package_id: str, install_path: str) -> None:
    write_yaml(
        workplace / "registries" / "installed-subjects.yaml",
        {
            "schema_version": 1,
            "subjects": [
                {
                    "id": package_id,
                    "type": "knowledge_package",
                    "scope": "global",
                    "version": "1.0.0",
                    "install_path": install_path,
                    "update_policy": {"mode": "manual"},
                }
            ],
        },
    )


def copy_package_to_workplace(hub: Path, workplace: Path, package_id: str) -> None:
    target = workplace / "packages" / package_id
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(hub / "packages" / package_id, target)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
