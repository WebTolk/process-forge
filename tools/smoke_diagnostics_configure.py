#!/usr/bin/env python3
"""Profile proposal policy and actual CLI no-write/apply behavior."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from processforge_core import diagnostics as d


def main():
    now = time.time()
    original = {"schema_version": 1, "sink": "none", "work": {"other": {"profile": "quiet"}}, "sessions": {"keep": {"profile": "off"}}}
    proposed, report = d.configure_proposal(original, "diagnostic", run_id="exact-work", duration=120, now=now)
    assert original["work"] == {"other": {"profile": "quiet"}}
    assert proposed["sessions"] == original["sessions"] and proposed["sink"] == "none"
    assert abs(d._epoch(report["change"]["expires_at"]) - now - 120) < 0.00001
    assert report["effective"]["values"]["profile"] == "diagnostic"
    expired = d.Logger(d.resolve_config(("project", proposed["work"]["exact-work"]), now=now))
    expired.values["expires_at"] = "2000-01-01T00:00:00Z"
    assert expired.effective()["values"]["profile"] == "normal"
    rejected = [({"profile": "quiet", "locked": ["profile"]}, {}),
                ({"work": {"one": {"profile": "quiet", "locked": ["profile"]}}}, {"run_id": "one"}),
                ({"work": []}, {}), ({"unsupported": True}, {}), ({}, {"duration": 901}),
                ({}, {"duration": 0}), ({}, {"duration": True}), ({}, {"run_id": "x", "session_id": "y"})]
    for document, kwargs in rejected:
        try:
            d.configure_proposal(document, "trace", now=now, **kwargs)
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid/locked proposal accepted")
    with tempfile.TemporaryDirectory(prefix="pf-profile spaces-") as temp:
        project = Path(temp)
        (project / ".pf").mkdir()
        (project / ".pf/process-forge.yaml").write_text("schema_version: 1\nid: fixture\n")
        path = project / ".pf/diagnostics.json"
        path.write_text(json.dumps(original))
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("PF_DIAGNOSTICS", None)
        command = [sys.executable, "-B", str(ROOT / "bin/pf.py"), "diagnostics-configure", "--project-root", str(project), "--profile", "diagnostic", "--session-id", "new", "--duration", "60"]
        before = {p.relative_to(project).as_posix(): p.read_bytes() for p in project.rglob("*") if p.is_file()}
        result = subprocess.run(command, capture_output=True, env=env, timeout=30)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["action"] == "plan"
        assert before == {p.relative_to(project).as_posix(): p.read_bytes() for p in project.rglob("*") if p.is_file()}
        result = subprocess.run([*command, "--apply"], capture_output=True, env=env, timeout=30)
        assert result.returncode == 0, result.stderr
        after = json.loads(path.read_text())
        assert after["work"] == original["work"] and after["sessions"]["keep"] == original["sessions"]["keep"]
        assert after["sessions"]["new"]["profile"] == "diagnostic"
        assert not (project / ".pf/runtime/events").exists() and not (project / ".pf/runtime/diagnostics").exists()
        path.write_text(json.dumps({"profile": "quiet", "locked": ["profile"]}))
        previous = path.read_bytes()
        assert subprocess.run([*command, "--apply"], capture_output=True, env=env, timeout=30).returncode != 0
        assert path.read_bytes() == previous
        path.write_bytes(b" " * 65537)
        assert subprocess.run(command, capture_output=True, env=env, timeout=30).returncode != 0
    print("PASS: diagnostics profile plan/apply, preservation, locks, expiry, bounds and no-write inspection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
