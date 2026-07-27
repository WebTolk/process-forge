#!/usr/bin/env python3
"""Validate software lifecycle artifact declarations."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
PROCESS = ROOT / "processes" / "software-feature-development.yaml"


REQUIRED_ARTIFACTS = {
    "brief",
    "scope",
    "task-record",
    "execution-context-summary",
    "lifecycle-mode-decision",
    "investigation-report",
    "impact-analysis",
    "domain-notes",
    "domain-model",
    "domain-rules",
    "architecture",
    "implementation-plan",
    "decision-log",
    "changed-files",
    "change-summary",
    "review-findings",
    "test-plan",
    "test-cases",
    "test-report",
    "browser-verification-report",
    "release-notes",
    "migration-notes",
    "patch",
    "delivery-plan",
    "delivery-report",
    "evolution-report",
    "updated-rules-or-extensions",
    "instruction-update-proposal",
    "knowledge-update-proposal",
}


def main() -> int:
    data = yaml.safe_load(PROCESS.read_text(encoding="utf-8"))
    definitions = {item["id"]: item for item in data["artifact_definitions"]}
    assert REQUIRED_ARTIFACTS <= set(definitions), sorted(REQUIRED_ARTIFACTS - set(definitions))
    produced = {artifact for stage in data["stages"] for artifact in stage.get("produced_artifacts", [])}
    assert produced <= set(definitions), sorted(produced - set(definitions))
    assert "updated-cursor" not in definitions
    browser = definitions["browser-verification-report"]
    assert browser.get("required") is False
    assert browser.get("required_when")
    assert set(browser.get("not_applicable_requires", [])) >= {"reason", "evidence"}
    instruction = definitions["instruction-update-proposal"]
    assert instruction.get("replaces_legacy_artifact") == "updated-cursor"
    print("PASS: software lifecycle artifacts smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

