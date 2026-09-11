"""Read-only semantic probes; mocked run loading, no production mutations."""
from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src")]
import yaml
import processforge as core
from processforge_core.process_execution import ProcessExecutionService
from processforge_core.core_update import workplace_migration_plan


def main() -> None:
    doc = (ROOT / "docs/concepts/assignment-front-matter.md").read_text(encoding="utf-8")
    metadata = yaml.safe_load(re.search(r"```markdown\s*---\s*\n(.*?)\n---", doc, re.S).group(1))
    outputs = core.normalize_required_outputs(metadata["required_outputs"])
    checks = core.required_output_checks(ROOT, {"required_outputs": outputs})
    assert outputs and "path" not in outputs[0]
    assert any(c.level == "FAIL" and "has no path" in c.message for c in checks)

    with patch.object(core, "load_run", return_value={"id": "release-prep", "tasks": [
        {"id": "task-001-docs", "status": "done"},
        {"id": "task-002-tests", "status": "ready"},
    ]}):
        try:
            core._command_run_complete_locked(argparse.Namespace(project_root=str(ROOT), run="release-prep", dry_run=True))
        except SystemExit as exc:
            batch_error = str(exc)
        else:
            raise AssertionError("Incomplete documented batch unexpectedly completed")
    assert "task-002-tests" in batch_error

    service = object.__new__(ProcessExecutionService)
    gates = {status: service._gate_state({}, "audit-gate", [{"kind": "gate", "id": "audit-gate", "status": status}], phase="exit")
             for status in ("pass", "passed", "approved", "not_applicable")}
    assert not gates["pass"]["satisfied"]
    assert all(gates[status]["satisfied"] for status in ("passed", "approved", "not_applicable"))
    migration = workplace_migration_plan(ROOT, ROOT / "not-opened.zip", installed_version="1.0.2", target_version="1.1.0", workplace_root=None)
    assert migration["status"] == "not_requested"
    report = {"method": "Pure contract calls; mocked load_run and dry_run prevent writes; no Core archive opened or update applied.",
              "assignment_front_matter": {"normalized_outputs": outputs, "checks": [dataclasses.asdict(c) for c in checks]},
              "incomplete_batch": {"error": batch_error}, "gate_vocabulary": gates,
              "update_without_workplace_root": migration}
    Path(__file__).with_name("semantic-probes.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
