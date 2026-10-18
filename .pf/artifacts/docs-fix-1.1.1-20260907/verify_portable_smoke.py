"""Run the documentation regression in a public-file copy without private .pf state."""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("public_inventory", ROOT / "tools/validate-process-forge-checksums.py")
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)
parent = ROOT / ".pf/tmp"
parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix="docs-public-copy-", dir=parent) as temporary:
    target = Path(temporary)
    count = 0
    for relative, source in inventory.public_file_entries(ROOT):
        if relative.startswith(".pf/"):
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        count += 1
    assert not (target / ".pf").exists()
    print(f"Copied {count} public inventory entries; no .pf state or Git metadata", flush=True)
    result = subprocess.run([sys.executable, str(target / "tools/smoke_docs_current_code_contract.py")], cwd=target)
    assert result.returncode == 0, result.returncode
    assert not (target / ".pf").exists(), "docs-only smoke unexpectedly created private state"
    print("PASS: documentation smoke runs from a public-file copy without private .pf")
