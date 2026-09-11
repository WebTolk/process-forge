"""Validate the actual documented required output before and after file creation."""
import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("docs_smoke", ROOT / "tools/smoke_docs_current_code_contract.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)
core = smoke.load_processforge_module()
assignment = smoke.assignment_example()
with tempfile.TemporaryDirectory(prefix="docs-output-contract-", dir=ROOT / ".pf/tmp") as temporary:
    project = Path(temporary)
    before = core.required_output_checks(project, assignment)
    assert any(item.level == "FAIL" and "missing" in item.message for item in before), before
    assert not any("has no path" in item.message for item in before), before
    for output in core.normalize_required_outputs(assignment["required_outputs"]):
        destination = project / output["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("# Example report\n\nVerified documentation fixture.\n", encoding="utf-8")
    after = core.required_output_checks(project, assignment)
    assert not any(item.level == "FAIL" for item in after), after
    assert any(item.level == "PASS" for item in after), after
    print("PASS: documented required output is missing before creation and PASS after creation; no path error")
