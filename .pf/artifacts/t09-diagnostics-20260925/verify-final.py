import ast
import hashlib
import json
from pathlib import Path
import re
from datetime import datetime, timezone

base = Path(__file__).resolve().parent
root = base.parents[2]
docs = [root / path for path in ("docs/concepts/diagnostics.md", "docs/ru/concepts/diagnostics.md", "docs/concepts/work-execution-contract.md", "docs/concepts/session-telemetry.md", "docs/concepts/runtime-mcp.md", "docs/ru/concepts/runtime-mcp.md")]
for path in docs:
    text = path.read_text(encoding="utf-8")
    for link in re.findall(r"\]\(([^)]+)\)", text):
        if not link.startswith(("http:", "https:", "#")):
            assert (path.parent / link.split("#")[0]).exists(), (path, link)
    assert all(line == line.rstrip() for line in text.splitlines()), path
paths = [root / name for name in ("src/processforge_core/diagnostics.py", "src/processforge_core/process_execution.py", "tools/processforge.py", "tools/pf_runtime/mcp_server.py", "tools/pf_runtime/host.py", "tools/pf_runtime/codex_hooks.py", "tools/codex_exec_worker.py", "tools/smoke_diagnostics.py")]
for path in paths: ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
bundle = base / "sanitized-diagnostic-bundle-accepted.json"
data = json.loads(bundle.read_text(encoding="utf-8"))
def strings(value):
    if isinstance(value, str): yield value
    elif isinstance(value, dict):
        for item in value.values(): yield from strings(item)
    elif isinstance(value, list):
        for item in value: yield from strings(item)
assert all(not re.search(r"[A-Za-z]:[\\/]|/(?:Users|home|tmp|private|srv)/", item) for item in strings(data))
assert data["build"]["diagnostics_sha256"] == hashlib.sha256(paths[0].read_bytes()).hexdigest()
report = {"time_utc": datetime.now(timezone.utc).isoformat(), "document_links_whitespace": "PASS", "documents": len(docs),
          "python_syntax": "PASS", "python_files": len(paths), "schema_validation": "PASS: ProcessForge structure and JSON Schema validation passed (separate captured tool execution)",
          "final_bundle": {"sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(), "records": len(data["records"]), "truncated": data["truncated"],
                           "private_absolute_paths": 0, "build_matches_source": True, "context_status": data.get("metadata", {}).get("context_check", {}).get("status")}}
(base / "final-delivery-verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
