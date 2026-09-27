import json
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "tools"))
import smoke_runtime_ledger_hooks_mcp as smoke
original = shutil.rmtree
preserved = []
def preserve(path, *args, **kwargs):
    resolved = Path(path).resolve()
    if resolved.parent == (root / ".pf/tmp").resolve() and resolved.name.startswith("pf-ledger-hooks-mcp-"):
        preserved.append(str(resolved))
        print("Preserved fixture:", resolved, flush=True)
        return
    return original(path, *args, **kwargs)
shutil.rmtree = preserve
try:
    smoke.main()
finally:
    shutil.rmtree = original
    Path(__file__).with_name("runtime-start-fixture.json").write_text(json.dumps(preserved, indent=2), encoding="utf-8")
