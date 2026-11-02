"""Real sealed external CLI/helper regressions for manifest-only Core updates."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import textwrap
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
QA = Path(
    os.environ.get(
        "PF_FILE_UPDATE_TEST_ROOT", str(ROOT.parent / "qa/file-update-tests")
    )
).resolve()
OLD = {
    "same.txt": b"same\n",
    "changed.txt": b"old\n",
    "removed.txt": b"removed\n",
    "missing.txt": b"missing\n",
    "old/sub/file.txt": b"obsolete\n",
}
NEW = {
    "same.txt": b"same\n",
    "changed.txt": b"new\n",
    "missing.txt": b"missing\n",
    "added.txt": b"added\n",
}
PRIVATE = {
    "processes/user/private.yaml": b"id: private-user\n",
    "processes/custom/nested/private.yml": b"id: private-custom\n",
    ".pf/runs/private.yaml": b"private project history\n",
    "runtime/user/keep": b"private runtime\n",
    "unknown.txt": b"unowned bytes\n",
}

PREAMBLE = """
import importlib.util, json, os, sys, types
from pathlib import Path
manager, case, target, archive = map(Path, sys.argv[1:5])
leaf=(manager/'tools/pf_native_control.py').read_bytes()
native=types.ModuleType('pf_native_control')
native.__file__=str(manager/'tools/pf_native_control.py')
native._captured_source=leaf
sys.modules[native.__name__]=native
exec(compile(leaf,native.__file__,'exec',dont_inherit=True),native.__dict__)
entry=native.bootstrap_entry(manager,trusted_leaf=leaf)
assert entry.publication is not None and entry.image is not None and entry.control is None
sys.path[:0]=[str(manager/'tools'),str(manager/'src')]
from processforge_core.maintenance.update import apply_update, CoreUpdateError, core_status, repair_status
from processforge_core.maintenance import file_update
def invoke(**options):
    try:
        return {'ok':True,'result':apply_update(target,archive,confirm=True,**options)}
    except CoreUpdateError as error:
        return {'ok':False,'code':error.code,'message':error.message}
def emit(value):
    (case/'probe-result.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(json.dumps(value,sort_keys=True))
"""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def put(root: Path, relative: str, raw: bytes) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def old_manifest(files: dict[str, bytes]) -> bytes:
    return (
        json.dumps(
            {
                "schema_version": 1,
                "kind": "processforge.core_manifest",
                "version": "1.0.0",
                "source": {"fixture": True},
                "generated_at": "fixture",
                "files": [
                    {"relative_path": path, "size": len(raw), "sha256": sha(raw)}
                    for path, raw in sorted(files.items())
                ],
            },
            indent=2,
        ).encode()
        + b"\n"
    )


def archive_bytes(build: Any) -> bytes:
    import io

    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for relative, raw in {
            **build.payload,
            "processforge-core.manifest.json": build.manifest,
        }.items():
            bundle.writestr(relative, raw)
    return stream.getvalue()


@pytest.fixture(scope="module")
def sealed() -> Any:
    assert QA.is_relative_to((ROOT.parent / "qa").resolve())
    base = QA / uuid.uuid4().hex
    base.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location(
        "file_update_fixture_native", ROOT / "tools/pf_native_control.py"
    )
    assert spec is not None and spec.loader is not None
    native = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = native
    spec.loader.exec_module(native)
    payload = {
        path.relative_to(ROOT).as_posix(): native.canonical_release_bytes(
            path.read_bytes()
        )
        for directory in ("src", "tools")
        for path in (ROOT / directory).rglob("*.py")
    }
    payload.update(
        {
            "bin/pf.py": (ROOT / "bin/pf.py").read_bytes(),
            "VERSION": b"1.0.0\n",
            native.INVENTORY: b"",
            **OLD,
        }
    )
    build = native.build_publication(
        payload,
        version="1.0.0",
        source={"fixture": "external file-update manager"},
        generated_at="fixture",
    )
    manager = (base / "manager").resolve()
    for relative, raw in {**build.payload, native.MANIFEST: build.manifest}.items():
        put(manager, relative, raw)

    def incoming(extra: dict[str, bytes] | None = None) -> Any:
        return native.build_publication(
            {
                native.LEAF: (ROOT / native.LEAF).read_bytes(),
                native.INVENTORY: b"",
                "VERSION": b"2.0.0\n",
                **NEW,
                **(extra or {}),
            },
            version="2.0.0",
            source={"fixture": True},
            generated_at="fixture",
        )

    return {
        "native": native,
        "manager": manager,
        "base": base,
        "incoming": incoming,
        "archive": archive_bytes(incoming()),
    }


@dataclass
class Harness:
    root: Path
    target: Path
    archive: Path
    manager: Path

    def run(self, body: str, *, timeout: int = 30) -> dict[str, Any]:
        script = self.root / ("probe-" + uuid.uuid4().hex + ".py")
        script.write_text(PREAMBLE + "\n" + textwrap.dedent(body), encoding="utf-8")
        return self.command(
            [
                sys.executable,
                "-I",
                "-B",
                str(script),
                str(self.manager),
                str(self.root),
                str(self.target),
                str(self.archive),
            ],
            script.stem,
            timeout=timeout,
        )

    def command(
        self, command: list[str], label: str, *, timeout: int = 30
    ) -> dict[str, Any]:
        result = subprocess.run(
            command,
            cwd=self.root,
            env={k: v for k, v in os.environ.items() if not k.startswith("PF_")},
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        (self.root / (label + ".stdout.log")).write_text(
            result.stdout, encoding="utf-8"
        )
        (self.root / (label + ".stderr.log")).write_text(
            result.stderr, encoding="utf-8"
        )
        (self.root / (label + ".command.json")).write_text(
            json.dumps(
                {
                    "command": command,
                    "cwd": str(self.root),
                    "exit_code": result.returncode,
                    "timeout": timeout,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads((self.root / "probe-result.json").read_text(encoding="utf-8"))

    def snapshot(self) -> dict[str, bytes]:
        names = {*OLD, *PRIVATE, "processforge-core.manifest.json"}
        return {
            name: (self.target / name).read_bytes()
            for name in names
            if (self.target / name).is_file()
        }

    def assert_no_apply(self, before: dict[str, bytes]) -> None:
        assert self.snapshot() == before
        assert not (self.target / "runtime/core-update/in-progress.json").exists()
        assert not (self.target / "runtime/core-update/last-apply.json").exists()
        assert not (self.target / "runtime/core-update/backups").exists()


@pytest.fixture
def fixture(sealed: Any) -> Harness:
    root = sealed["base"] / uuid.uuid4().hex
    target = root / "target"
    target.mkdir(parents=True)
    for relative, raw in {
        **OLD,
        **PRIVATE,
        "processforge-core.manifest.json": old_manifest(OLD),
    }.items():
        put(target, relative, raw)
    archive = root / "incoming.zip"
    archive.write_bytes(sealed["archive"])
    return Harness(root, target.resolve(), archive, sealed["manager"])


def test_actual_external_sealed_cli_updates_manifest_only_target(
    fixture: Harness,
) -> None:
    script = """
import json, subprocess, sys
from pathlib import Path
manager,case,target,archive=map(Path,sys.argv[1:])
command=[sys.executable,'-I','-B',str(manager/'bin/pf.py'),'core-update','apply','--core-root',str(target),'--archive',str(archive),'--confirm']
result=subprocess.run(command,cwd=case,capture_output=True,text=True,timeout=30)
(case/'actual-cli.stdout.log').write_text(result.stdout)
(case/'actual-cli.stderr.log').write_text(result.stderr)
(case/'actual-cli.command.json').write_text(json.dumps({'command':command,'exit_code':result.returncode},indent=2))
assert result.returncode==0,result.stdout+result.stderr
(case/'probe-result.json').write_text(result.stdout)
"""
    # The real launcher is an accepted payload member too.
    launcher = fixture.manager / "bin/pf.py"
    assert launcher.is_file()
    path = fixture.root / "actual-cli-driver.py"
    path.write_text(textwrap.dedent(script), encoding="utf-8")
    result = fixture.command(
        [
            sys.executable,
            "-I",
            "-B",
            str(path),
            str(fixture.manager),
            str(fixture.root),
            str(fixture.target),
            str(fixture.archive),
        ],
        "cli-driver",
    )
    assert result["status"] == "applied" and result["maintenance_mode"] == "file_only"
    for relative, raw in NEW.items():
        assert (fixture.target / relative).read_bytes() == raw
    for relative, raw in PRIVATE.items():
        assert (fixture.target / relative).read_bytes() == raw
    assert not (fixture.target / "removed.txt").exists()
    assert not (fixture.target / "old").exists()
    assert not (fixture.target / "runtime/native-control").exists()
    assert not (fixture.target / "runtime/managed-ingress").exists()


@pytest.mark.parametrize("direct", [False, True])
def test_same_root_file_update_refuses_without_writes(
    fixture: Harness, direct: bool
) -> None:
    fixture.target = fixture.manager
    before = fixture.snapshot()
    body = """
try:
    result=file_update.apply_file_update(target,archive,workplace_root=None) if DIRECT else apply_update(target,archive,confirm=True)
except CoreUpdateError as error:
    emit({'code':error.code})
else:
    raise AssertionError('same-root file updater accepted')
""".replace("DIRECT", repr(direct))
    assert fixture.run(body)["code"] == "plan_blocked"
    fixture.assert_no_apply(before)


def test_actual_preimages_missing_owned_and_private_data_survive(
    fixture: Harness,
) -> None:
    preimages = {
        "same.txt": b"local unchanged release path\n",
        "changed.txt": b"local changed path\n",
        "removed.txt": b"local removed preimage\n",
    }
    for name, raw in preimages.items():
        (fixture.target / name).write_bytes(raw)
    (fixture.target / "missing.txt").unlink()
    original_manifest = (
        fixture.target / "processforge-core.manifest.json"
    ).read_bytes()
    result = fixture.run("emit(invoke())")
    assert result["ok"], result
    receipt = result["result"]
    backup = Path(receipt["backup_dir"])
    for name, raw in preimages.items():
        assert (backup / receipt["backed_up"][name]).read_bytes() == raw
    assert receipt["backed_up"]["missing.txt"] is None
    assert (backup / "control/old-manifest.json").read_bytes() == original_manifest
    assert receipt["counts"]["restored"] == 1
    for name, raw in {**NEW, **PRIVATE}.items():
        assert (fixture.target / name).read_bytes() == raw


@pytest.mark.parametrize("stage", ["payload", "manifest", "last_record"])
def test_failed_file_operations_leave_truthful_recovery_journal(
    fixture: Harness, stage: str
) -> None:
    original_manifest = (
        fixture.target / "processforge-core.manifest.json"
    ).read_bytes()
    (fixture.target / "changed.txt").write_bytes(b"real local preimage\n")
    result = fixture.run(
        """
original_replace=file_update.os.replace
failure={'payload':target/'changed.txt','manifest':target/'processforge-core.manifest.json','last_record':target/'runtime/core-update/last-apply.json'}[STAGE]
def fail(source,destination):
    if Path(destination)==failure:raise PermissionError(13,'controlled owned-fixture denial')
    return original_replace(source,destination)
file_update.os.replace=fail
try:
    result=invoke()
finally:
    file_update.os.replace=original_replace
result['status']=core_status(target)
result['repair']=repair_status(target)
emit(result)
""".replace("STAGE", repr(stage))
    )
    assert result["code"] == "file_operation_failed"
    progress = result["status"]["in_progress"]
    assert progress["status"] == "failed"
    assert isinstance(progress["pending_operations"], list)
    assert bool(progress["pending_operations"]) is (stage != "last_record")
    assert result["status"]["incomplete_update"] is True
    backup = Path(progress["backup_dir"])
    assert (
        backup / progress["backed_up"]["changed.txt"]
    ).read_bytes() == b"real local preimage\n"
    assert (backup / "control/old-manifest.json").read_bytes() == original_manifest
    assert result["repair"]["status"] == (
        "manual_repair_required" if stage == "last_record" else "safe_to_rollback"
    )
    for relative, raw in PRIVATE.items():
        assert (fixture.target / relative).read_bytes() == raw


@pytest.mark.parametrize("name", ["native-control", "managed-ingress"])
@pytest.mark.parametrize("kind", ["empty_directory", "partial_file"])
def test_complete_or_partial_managed_markers_never_fall_back(
    fixture: Harness, name: str, kind: str
) -> None:
    marker = fixture.target / "runtime" / name
    marker.parent.mkdir(exist_ok=True)
    marker.mkdir() if kind == "empty_directory" else marker.write_bytes(
        b"partial metadata"
    )
    before = fixture.snapshot()
    result = fixture.run("""
def forbidden(*args,**kwargs):raise AssertionError('managed target entered compatibility updater')
file_update.apply_file_update=forbidden
emit(invoke())
""")
    assert result["code"] == "plan_blocked"
    fixture.assert_no_apply(before)
    assert marker.exists()


def test_managed_caller_cannot_fall_back_to_unbound_target(fixture: Harness) -> None:
    before = fixture.snapshot()
    result = fixture.run("""
from dataclasses import replace
guard,epoch=case/'gate',case/'epoch'
guard.write_bytes(b'0');epoch.write_bytes(b'fixture')
native._ENTRY=replace(entry,control=native.NativeControl(guard,epoch,'fixture'))
def forbidden(*args,**kwargs):raise AssertionError('managed caller entered compatibility updater')
file_update.apply_file_update=forbidden
emit(invoke(force_local_modifications=True))
""")
    assert result["code"] == "plan_blocked"
    fixture.assert_no_apply(before)


def test_archive_path_replacement_cannot_change_frozen_input(
    fixture: Harness, sealed: Any
) -> None:
    expected_hash = sha(fixture.archive.read_bytes())
    (fixture.root / "replacement.zip").write_bytes(
        archive_bytes(
            sealed["incoming"]({"changed.txt": b"wrong replacement archive\n"})
        )
    )
    result = fixture.run("""
planner=file_update._build_plan
def replace_original_path(*args,**kwargs):
    archive.write_bytes((case/'replacement.zip').read_bytes())
    return planner(*args,**kwargs)
file_update._build_plan=replace_original_path
emit(invoke())
""")
    assert result["ok"]
    assert result["result"]["archive_sha256"] == expected_hash
    assert sha(fixture.archive.read_bytes()) != expected_hash
    assert (fixture.target / "changed.txt").read_bytes() == NEW["changed.txt"]


@pytest.mark.parametrize(
    "fault", ["not_zip", "tampered_payload", "duplicate_member", "unsealed"]
)
def test_invalid_archive_preserves_target(fixture: Harness, fault: str) -> None:
    if fault == "not_zip":
        fixture.archive.write_bytes(b"not a ZIP")
    elif fault == "unsealed":
        with zipfile.ZipFile(fixture.archive, "w") as bundle:
            bundle.writestr("changed.txt", b"new\n")
            bundle.writestr(
                "processforge-core.manifest.json",
                old_manifest({"changed.txt": b"new\n"}),
            )
    else:
        with zipfile.ZipFile(fixture.archive) as bundle:
            entries = {name: bundle.read(name) for name in bundle.namelist()}
        with zipfile.ZipFile(fixture.archive, "w") as bundle:
            for name, raw in entries.items():
                bundle.writestr(
                    name,
                    b"tampered\n"
                    if fault == "tampered_payload" and name == "changed.txt"
                    else raw,
                )
            if fault == "duplicate_member":
                with pytest.warns(UserWarning, match="Duplicate name"):
                    bundle.writestr("changed.txt", entries["changed.txt"])
    before = fixture.snapshot()
    result = fixture.run("emit(invoke())")
    assert not result["ok"]
    fixture.assert_no_apply(before)


@pytest.mark.parametrize(
    "relative",
    [
        "processes/user/private.yaml",
        "processes/custom/private.yaml",
        ".pf/runs/private.yaml",
        "runtime/private.txt",
        "Processes/USER/private.yaml",
    ],
)
@pytest.mark.parametrize("which", ["old", "new"])
def test_manifest_cannot_claim_private_or_runtime_paths(
    fixture: Harness, sealed: Any, relative: str, which: str
) -> None:
    if which == "old":
        put(fixture.target, relative, b"protected\n")
        (fixture.target / "processforge-core.manifest.json").write_bytes(
            old_manifest({**OLD, relative: b"protected\n"})
        )
    else:
        fixture.archive.write_bytes(
            archive_bytes(
                sealed["incoming"]({relative: b"untrusted private payload\n"})
            )
        )
    before = fixture.snapshot()
    result = fixture.run("emit(invoke())")
    assert result.get("code") == "plan_blocked", result
    fixture.assert_no_apply(before)


@pytest.mark.parametrize(
    "kind", ["unowned_file", "unowned_directory", "hardlink", "junction"]
)
def test_collisions_and_link_boundaries_preserve_foreign_objects(
    fixture: Harness, kind: str
) -> None:
    if kind == "unowned_file":
        put(fixture.target, "added.txt", b"foreign collision\n")
    elif kind == "unowned_directory":
        put(fixture.target, "added.txt/foreign", b"foreign nested collision\n")
    elif kind == "hardlink":
        os.link(fixture.target / "changed.txt", fixture.root / "external-hardlink")
    else:
        original = fixture.target / "old"
        original.rename(fixture.root / "saved-original")
        external = fixture.root / "external-junction-target"
        put(external, "sub/file.txt", b"foreign junction bytes\n")
        created = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(original), str(external)],
            capture_output=True,
            timeout=10,
            check=False,
        )
        assert created.returncode == 0, created.stdout + created.stderr
    before = fixture.snapshot()
    result = fixture.run("emit(invoke())")
    assert not result["ok"]
    fixture.assert_no_apply(before)
    if kind == "hardlink":
        assert (fixture.root / "external-hardlink").read_bytes() == OLD["changed.txt"]
    if kind == "junction":
        assert (
            fixture.root / "external-junction-target/sub/file.txt"
        ).read_bytes() == b"foreign junction bytes\n"


def test_known_workplace_live_pid_blocks_without_endpoint_contact(
    fixture: Harness,
) -> None:
    before = fixture.snapshot()
    result = fixture.run("""
workplace=case/'workplace'
import pf_runtime.service as service
state=service.service_path(workplace)
state.parent.mkdir(parents=True)
state.write_text(json.dumps({'pid':os.getpid(),'status':'stopped','instance_id':'fixture'}))
def forbidden(*args,**kwargs):raise AssertionError('endpoint contact during offline refusal')
service.http_json=forbidden
emit(invoke(workplace_root=workplace))
""")
    assert result["code"] == "plan_blocked"
    assert "stop" in result["message"].lower()
    fixture.assert_no_apply(before)


def test_real_file_mutex_excludes_contender_until_release(fixture: Harness) -> None:
    body = """
import subprocess,time
from processforge_core.runtime.execution_admission import registry_file_lock
lock=target/'runtime/core-update/file-maintenance'
child_script=case/'contender.py'
child_script.write_text(PREAMBLE_TEXT+"\\nprint('attempting',flush=True)\\nemit(invoke())\\n")
command=[sys.executable,'-I','-B',str(child_script),str(manager),str(case),str(target),str(archive)]
(case/'contender.command.json').write_text(json.dumps({'command':command},indent=2))
with registry_file_lock(lock,timeout_seconds=1,stale_after_seconds=0):
    child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    assert child.stdout.readline().strip()=='attempting'
    time.sleep(0.25)
    assert child.poll() is None
    assert not (target/'runtime/core-update/in-progress.json').exists()
    assert (target/'changed.txt').read_bytes()==b'old\\n'
stdout,stderr=child.communicate(timeout=20)
(case/'contender.stdout.log').write_text(stdout)
(case/'contender.stderr.log').write_text(stderr)
assert child.returncode==0,stdout+stderr
result=json.loads((case/'probe-result.json').read_text())
assert result['ok'],result
emit({'serialized':True,'result':result['result']})
""".replace("PREAMBLE_TEXT", repr(PREAMBLE))
    assert fixture.run(body)["serialized"]


def test_actual_same_root_cli_refuses_without_mutation(fixture: Harness) -> None:
    fixture.target = fixture.manager
    before = fixture.snapshot()
    result = fixture.run("""
import subprocess
command=[sys.executable,'-I','-B',str(manager/'bin/pf.py'),'core-update','apply','--core-root',str(manager),'--archive',str(archive),'--confirm']
result=subprocess.run(command,cwd=case,capture_output=True,text=True,timeout=30)
(case/'same-root-cli.stdout.log').write_text(result.stdout)
(case/'same-root-cli.stderr.log').write_text(result.stderr)
(case/'same-root-cli.command.json').write_text(json.dumps({'command':command,'exit_code':result.returncode},indent=2))
assert result.returncode==1,result.stdout+result.stderr
emit(json.loads(result.stdout)['error'])
""")
    assert result["code"] == "plan_blocked"
    fixture.assert_no_apply(before)


@pytest.mark.parametrize("name", ["native-control", "managed-ingress"])
def test_unreadable_managed_marker_is_not_treated_as_absent(
    fixture: Harness, name: str
) -> None:
    before = fixture.snapshot()
    result = fixture.run(
        """
original=Path.lstat
def inaccessible(path,*args,**kwargs):
    if path==target/'runtime'/MARKER:raise PermissionError(13,'fixture marker inaccessible')
    return original(path,*args,**kwargs)
Path.lstat=inaccessible
try:result=invoke()
finally:Path.lstat=original
emit(result)
""".replace("MARKER", repr(name))
    )
    assert result["code"] == "plan_blocked"
    assert "inspect" in result["message"]
    fixture.assert_no_apply(before)


@pytest.mark.parametrize("collision", ["frozen_archive", "staging"])
def test_foreign_control_file_collision_is_never_deleted(
    fixture: Harness, collision: str
) -> None:
    token = "f" * 32
    relative = (
        f"runtime/core-update/archive-{token}.zip"
        if collision == "frozen_archive"
        else f"runtime/core-update/.in-progress.json.{token}.pf-update-tmp"
    )
    put(fixture.target, relative, b"foreign collision evidence\n")
    before = fixture.snapshot()
    result = fixture.run("""
from types import SimpleNamespace
file_update.uuid=SimpleNamespace(uuid4=lambda:SimpleNamespace(hex='f'*32))
native._update_now=lambda:'fixture'
emit(invoke())
""")
    assert result["code"] == "plan_blocked"
    assert fixture.snapshot() == before
    assert (fixture.target / relative).read_bytes() == b"foreign collision evidence\n"
    assert not (fixture.target / "runtime/core-update/in-progress.json").exists()


def test_linked_update_control_directory_refuses_cleanly(fixture: Harness) -> None:
    foreign = fixture.root / "foreign-control"
    put(foreign, "keep", b"foreign control evidence\n")
    link = fixture.target / "runtime/core-update"
    created = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(foreign)],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert created.returncode == 0, created.stdout + created.stderr
    before = fixture.snapshot()
    result = fixture.run("emit(invoke())")
    assert result["code"] == "plan_blocked"
    fixture.assert_no_apply(before)
    assert list(foreign.iterdir()) == [foreign / "keep"]
    assert (foreign / "keep").read_bytes() == b"foreign control evidence\n"
