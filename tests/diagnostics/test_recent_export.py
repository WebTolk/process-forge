"""Synthetic rotations and exception metadata; never read runtime logs."""

import json

import pytest

from processforge_core import diagnostics as diag


@pytest.fixture
def logs(tmp_path, monkeypatch):
    monkeypatch.setattr(diag.time, "time", lambda: 1000.0)
    monkeypatch.setattr(diag, "configuration", lambda *a, **k: diag.resolve_config())
    monkeypatch.setattr(diag, "build_identity", lambda: {})
    root = tmp_path / ".pf/runtime/diagnostics"
    root.mkdir(parents=True)
    return tmp_path, root


def record(code, timestamp="1970-01-01T00:16:40Z", **context):
    return {
        "timestamp": timestamp,
        "code": code,
        "identity": {"request_id": "request", "run_id": "run"},
        "context": context,
    }


def export(logs, **filters):
    project, _ = logs
    output = project / "bundle.json"
    result = diag.export_bundle(project, output, **filters)
    raw = output.read_bytes()
    assert len(raw) <= 4 * 1024 * 1024
    return result, json.loads(raw)


def test_current_file_survives_old_rotation_input_budget(logs):
    _, root = logs
    recent = record("recent", password="canary", note="canary", path="C:/private/file")
    (root / "diagnostics.jsonl").write_bytes(diag.encode(recent))
    old = diag.encode(record("old", "1970-01-01T00:00:00Z", pad="x" * 15000))
    for index in range(1, 8):
        (root / f"diagnostics.{index}.jsonl").write_bytes(old * 69)
    result, bundle = export(
        logs,
        since="1970-01-01T00:16:39Z",
        until="1970-01-01T00:16:41Z",
        request_id="request",
    )
    assert [r["code"] for r in bundle["records"]] == ["recent"]
    assert result["truncated"] is True
    assert bundle["manifest"][0]["name"] == "diagnostics.jsonl"
    assert sum(m.get("read_bytes", 0) for m in bundle["manifest"]) <= 4 * 1024 * 1024
    rendered = json.dumps(bundle)
    assert "canary" not in rendered and "C:/private" not in rendered


def test_chronology_and_equal_timestamp_visit_order(logs):
    _, root = logs
    (root / "diagnostics.jsonl").write_bytes(
        diag.encode(record("current-a")) + diag.encode(record("current-b"))
    )
    (root / "diagnostics.1.jsonl").write_bytes(
        diag.encode(record("older", "1970-01-01T00:16:39Z"))
        + diag.encode(record("rotation-tie"))
    )
    _, bundle = export(logs, run_id="run")
    assert [r["code"] for r in bundle["records"]] == [
        "older",
        "current-a",
        "current-b",
        "rotation-tie",
    ]


def test_record_cap_preserves_current_file(logs):
    _, root = logs
    (root / "diagnostics.jsonl").write_bytes(diag.encode(record("current")) * 2001)
    (root / "diagnostics.1.jsonl").write_bytes(diag.encode(record("rotation")))
    result, bundle = export(logs)
    assert result["records"] == 2000 and result["truncated"]
    assert {r["code"] for r in bundle["records"]} == {"current"}


def test_export_refuses_linked_known_file(logs):
    project, root = logs
    target = project / "synthetic.jsonl"
    target.write_bytes(diag.encode(record("target")))
    try:
        (root / "diagnostics.jsonl").symlink_to(target)
    except OSError:
        pytest.skip("host does not permit symlink creation")
    with pytest.raises(ValueError, match="linked inputs"):
        export(logs)
    assert not (project / "bundle.json").exists()


def test_malformed_record_is_rejected_without_repair(logs):
    _, root = logs
    raw = b'{"timestamp":null}\n' + diag.encode(record("valid"))
    path = root / "diagnostics.jsonl"
    path.write_bytes(raw)
    _, bundle = export(logs)
    assert bundle["rejected_records"] == 1
    assert [r["code"] for r in bundle["records"]] == ["valid"]
    assert path.read_bytes() == raw


def test_output_budget_trims_old_rotations_before_chronological_sort(logs):
    _, root = logs
    # NaN becomes the longer safe non-finite placeholder. Both input files fit
    # the input cap while their sanitized records exceed the output cap.
    context = {f"v{i}": [float("nan")] * 32 for i in range(20)}
    line = (json.dumps(record("current", **context)) + "\n").encode()
    old = (
        json.dumps(record("rotation", "1970-01-01T00:16:39Z", **context)) + "\n"
    ).encode()
    assert len(line) * 100 + len(old) * 700 < 4 * 1024 * 1024
    (root / "diagnostics.jsonl").write_bytes(line * 100)
    (root / "diagnostics.1.jsonl").write_bytes(old * 700)
    _, bundle = export(logs)
    assert bundle["truncated"] and len(bundle["records"]) < 800
    assert sum(r["code"] == "current" for r in bundle["records"]) == 100
    assert len(diag.encode(bundle)) <= 4 * 1024 * 1024


def traceback_error(depth):
    def innermost():
        raise RuntimeError("token=canary C:/private/location")

    def recurse(left):
        if left:
            recurse(left - 1)
        else:
            innermost()

    try:
        recurse(depth)
    except RuntimeError as error:
        return error


@pytest.mark.parametrize("depth,scan_cut", [(12, False), (80, True)])
def test_tail_frames_and_explicit_bounded_scan(depth, scan_cut):
    error = traceback_error(depth)
    error.admission_reason = "contention_timeout"
    error.admission_phase = "acquire"
    error.registry_lock_phase = "guard"
    error.admission_errno = 13
    error.private_lock_path = "C:/private/lock"
    cleaner = diag.Sanitizer(diag.DEFAULTS, export=True)
    clean = cleaner.clean(error)
    assert len(clean["frames"]) == diag.DEFAULTS["stack_frames"]
    assert clean["frames_truncated"] and cleaner.truncated
    assert clean["traceback_scan_truncated"] is scan_cut
    if not scan_cut:
        assert clean["frames"][-1]["function"] == "innermost"
    assert clean["admission_reason"] == "contention_timeout"
    assert clean["registry_lock_phase"] == "guard"
    assert clean["admission_errno"] == 13
    assert "private_lock_path" not in clean
    rendered = json.dumps(clean)
    assert "canary" not in rendered and "C:/private" not in rendered
    assert all("/" not in f["file"] and "\\" not in f["file"] for f in clean["frames"])


def test_hostile_and_malformed_exception_metadata():
    class Hostile(OSError):
        @property
        def registry_lock_phase(self):
            raise SystemExit("hostile getter")

    error = Hostile()
    error.registry_lock_reason = ["contention_timeout"]
    error.admission_reason = "C:/private/lock"
    error.admission_phase = "x" * 10000
    error.admission_errno = True
    error.admission_winerror = 1 << 1000
    assert diag.admission_facts(error) == {}
