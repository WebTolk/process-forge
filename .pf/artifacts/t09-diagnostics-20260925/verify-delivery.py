import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile
from datetime import datetime, timezone

base = Path(__file__).resolve().parent
root = base.parents[2]
bundle = base / "sanitized-diagnostic-bundle.json"
data = json.loads(bundle.read_text(encoding="utf-8"))
def strings(value):
    if isinstance(value, str): yield value
    elif isinstance(value, dict):
        for item in value.values(): yield from strings(item)
    elif isinstance(value, list):
        for item in value: yield from strings(item)
private = [value for value in strings(data) if re.search(r"[A-Za-z]:[\\/]|/(?:Users|home|tmp|private|srv)/", value)]
assert not private, private
proof = {"time_utc": datetime.now(timezone.utc).isoformat(), "bundle": {"sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
         "records": len(data["records"]), "truncated": data["truncated"], "private_absolute_paths": 0,
         "context_status": data.get("metadata", {}).get("context_check", {}).get("status")}}
fixture = Path(json.loads((base / "runtime-start-fixture.json").read_text(encoding="utf-8"))[0]).resolve()
scope = (root / ".pf/tmp").resolve()
assert fixture.parent == scope and fixture.name.startswith("pf-ledger-hooks-mcp-")
state = json.loads((fixture / "workplace/runtime/pf-runtime/service.json").read_text(encoding="utf-8"))
assert state["status"] == "stopped", state["status"]
archive = base / "runtime-start-fixture.zip"
with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as handle:
    for path in sorted(fixture.rglob("*")):
        if path.is_file() and not path.is_symlink():
            handle.write(path, path.relative_to(fixture).as_posix())
with zipfile.ZipFile(archive) as handle:
    assert handle.testzip() is None
    count = len(handle.infolist())
proof["runtime_fixture"] = {"status": "stopped", "files_archived": count, "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                            "first_failure": "one batch startup exit 1; initial fixture cleaned by test; root cause not reproduced",
                            "followup": "isolated preserved-fixture PASS and final assurance rerun PASS"}
shutil.rmtree(fixture)  # resolved direct child of dedicated .pf/tmp, stopped, archived and CRC-checked
proof["runtime_fixture"]["removed_after_archive"] = not fixture.exists()
(base / "delivery-verification.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
print(json.dumps(proof, indent=2))
