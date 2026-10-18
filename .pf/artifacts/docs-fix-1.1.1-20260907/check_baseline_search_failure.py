"""Reproduce the unrelated search smoke using tracked HEAD code in an isolated copy."""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("inventory", ROOT / "tools/validate-process-forge-checksums.py")
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)
with tempfile.TemporaryDirectory(prefix="docs-baseline-search-", dir=ROOT / ".pf/tmp") as temporary:
    target = Path(temporary)
    restored = 0
    for relative, source in inventory.public_file_entries(ROOT):
        source_relative = source.relative_to(ROOT).as_posix()
        result = subprocess.run(["git", "show", f"HEAD:{source_relative}"], cwd=ROOT, capture_output=True)
        if result.returncode:
            continue  # New untracked public regression is not part of HEAD.
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(result.stdout)
        restored += 1
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    print(f"Restored {restored} tracked public entries from HEAD {revision}; main worktree untouched", flush=True)
    result = subprocess.run([sys.executable, str(target / "tools/smoke_garage_no_hooks_sessionless.py")], cwd=target, text=True, encoding="utf-8", capture_output=True)
    print(result.stdout + result.stderr, flush=True)
    assert result.returncode != 0 and "empty_corpus" in result.stderr and "GarageNoHooksNeedle" in result.stderr, result.returncode
    print("CONFIRMED: unchanged HEAD reproduces the same empty-corpus search failure; not a documentation-change regression")
