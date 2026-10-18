#!/usr/bin/env python3
"""Private F02 evidence: compare the pinned pre-fix updater with the repair."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import types
import uuid
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "src"
BASELINE_REVISION = "1aecc18b6824204ca45ab30241b92d26e6d583a5"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def load_smoke_helpers():
    path = ROOT / "tools" / "smoke_core_update_manifest.py"
    spec = importlib.util.spec_from_file_location("public_core_update_smoke", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load smoke helpers: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_baseline() -> types.ModuleType:
    source = subprocess.check_output(
        ["git", "show", f"{BASELINE_REVISION}:src/processforge_core/core_update.py"],
        cwd=ROOT,
    )
    module = types.ModuleType("baseline_core_update")
    module.__file__ = f"{BASELINE_REVISION}:src/processforge_core/core_update.py"
    sys.modules[module.__name__] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


def run_fixture(root: Path, updater, helpers):
    core = root / f"core-{uuid.uuid4().hex}"
    core.mkdir()
    helpers.install_old_core(core)
    user_file = core / "user-note.txt"
    user_file.write_text("USER OWNED DATA", encoding="utf-8")
    archive = root / f"candidate-{uuid.uuid4().hex}.zip"
    helpers.write_archive(
        archive,
        {"a.txt": "old-a", "dir/b.txt": "old-b", "dir/c.txt": "same-c", "user-note.txt": "NEW CORE PAYLOAD"},
    )
    plan = updater.build_plan(core, archive)
    apply_error = None
    result = None
    try:
        result = updater.apply_update(core, archive, confirm=True)
    except Exception as exc:  # evidence records the expected repaired refusal
        apply_error = getattr(exc, "code", type(exc).__name__)
    return {
        "plan_status": plan["status"],
        "blockers": plan["blockers"],
        "apply_status": result["status"] if result else None,
        "apply_error": apply_error,
        "user_payload_after": user_file.read_text(encoding="utf-8"),
        "backed_up": result["backed_up"] if result else None,
    }


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: baseline_collision_repro.py <precreated-scratch-root>")
    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    helpers = load_smoke_helpers()
    baseline = load_baseline()
    from processforge_core import core_update as repaired

    payload = {
        "baseline_revision": BASELINE_REVISION,
        "baseline": run_fixture(root, baseline, helpers),
        "repaired": run_fixture(root, repaired, helpers),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
