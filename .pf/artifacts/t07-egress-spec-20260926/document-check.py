"""Validate design-package integrity, not the proposed privacy engine."""
import ast
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
result = {"kind": "t07.document-check", "recorded_at": datetime.now(timezone.utc).isoformat(), "checks": {}}
output_name = sys.argv[1] if len(sys.argv) > 1 else "document-check-result.json"
assert output_name in {"document-check-result.json", "document-check-assurance.json", "document-check-final.json"}
output_path = HERE / output_name
assert not output_path.exists(), "Preserve previous observation; choose an unused declared evidence filename"


def read_json(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def check():
    documents = list(HERE.glob("*.md"))
    link_count = 0
    for path in documents:
        body = path.read_text(encoding="utf-8")
        assert "\ufffd" not in body, path.name
        assert not path.read_bytes().startswith(b"\xef\xbb\xbf"), path.name
        assert all(line == line.rstrip() for line in body.splitlines()), path.name
        for link in re.findall(r"\]\(([^)]+)\)", body):
            if link.startswith(("https:", "http:", "#")):
                continue
            assert (path.parent / link.split("#")[0]).resolve().exists(), (path.name, link)
            link_count += 1
    result["checks"]["documents"] = {"count": len(documents), "existing_local_links": link_count}

    anchors = read_json("source-map.json")["symbols"]
    source_cache = {}
    for entry in anchors:
        path = ROOT / entry["path"]
        if entry["path"] not in source_cache:
            parsed = ast.parse(path.read_text(encoding="utf-8-sig"))
            definitions = {(n.name, n.lineno) for n in ast.walk(parsed) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
            source_cache[entry["path"]] = (hashlib.sha256(path.read_bytes()).hexdigest(), definitions)
        digest, definitions = source_cache[entry["path"]]
        assert digest == entry["sha256"] and (entry["symbol"], entry["line"]) in definitions, entry
    result["checks"]["source_anchors"] = {"symbols": len(anchors), "files": len({a["path"] for a in anchors})}

    matrix = read_json("acceptance-matrix.json")
    required = set(re.findall(r"- (R\d\d):", (HERE / "scope.md").read_text(encoding="utf-8")))
    threats = set(re.findall(r"\| (H\d\d) \|", (HERE / "threat-model.md").read_text(encoding="utf-8")))
    assert set(matrix["requirements"]) == required and len(required) == 9
    assert set(matrix["threats"]) == threats and len(threats) == 14
    assert matrix["design_only"] is True and matrix["kind"].endswith(".proposal")
    cases = matrix["cases"]
    assert len(cases) == len({c["id"] for c in cases}) == 28
    for case in cases:
        assert set(case["requirements"]) <= required and case["requirements"], case["id"]
        assert set(case["threats"]) <= threats and case["threats"], case["id"]
        assert case["status"] == "not_run" and case["phase"] == "future_implementation", case["id"]
        assert all(isinstance(case[key], str) and len(case[key]) >= 20 for key in ("scenario", "expected", "evidence")), case["id"]
    assert set().union(*(set(c["requirements"]) for c in cases)) == required
    assert set().union(*(set(c["threats"]) for c in cases)) == threats
    result["checks"]["traceability"] = {"requirements": sorted(required), "threats": sorted(threats), "future_cases": len(cases), "runtime_cases_executed": 0}

    examples = read_json("examples.json")
    assert examples["design_only"] is True and examples["kind"].endswith(".proposal")
    assert len(examples["examples"]) == len({e["id"] for e in examples["examples"]}) == 5
    for entry in examples["examples"]:
        action = entry["decision"]["action"]
        assert action in {"allow", "redact", "block"}
        view = entry["recipient_view"]
        if action == "block":
            assert view is None and entry["decision"]["assurance"] == "none"
            continue
        assert set(view) == {"kind", "version", "attempt_alias", "units"}
        assert view["kind"] == "pf.outbound-view.proposal" and view["version"] == 1
        assert re.fullmatch(r"attempt-opaque-\d\d", view["attempt_alias"])
        for unit in view["units"]:
            assert set(unit) == {"id", "text", "transformed"}
            assert isinstance(unit["transformed"], bool) and isinstance(unit["text"], str)
            assert unit["transformed"] == (action == "redact")
            assert (unit["text"] == entry["input"]["text"]) == (action == "allow")
        serialized = json.dumps(view)
        assert all(key not in serialized for key in entry["local_only_fields"])
        assert not re.search(r"[A-Za-z]:[\\/]|/Users/|/home/", serialized)
    result["checks"]["example_structure"] = {"examples": 5, "product_schema_validation": "not_applicable_proposal"}

    baseline = read_json("baseline.json")["files"]
    changed = [p for p, h in baseline.items() if not (ROOT / p).is_file() or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h]
    assert not changed, changed
    current = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    added_product = [p for p in current if p and not p.startswith(".pf/") and p not in baseline and (ROOT / p).is_file()]
    assert not added_product, added_product
    result["checks"]["preservation"] = {"protected_files": len(baseline), "changed": changed, "added_product_files": added_product}
    diff = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    result["checks"]["git_diff_check"] = {"exit_code": diff.returncode, "stdout": diff.stdout, "stderr": diff.stderr}
    assert diff.returncode == 0


try:
    check()
except Exception as exc:
    result["status"] = "FAIL"
    result["error"] = str(exc)
    raise
else:
    result["status"] = "PASS"
finally:
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": {k: v for k, v in result["checks"].items() if k != "git_diff_check"}}, ensure_ascii=False))
