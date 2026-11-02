"""Force-stop policy models plus real Windows handles and a controlled child."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import textwrap
import uuid
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASE_PYTHON = str(getattr(sys, "_base_executable"))
QA = Path(
    os.environ.get(
        "OWNED_SHUTDOWN_TEST_ROOT", str(ROOT.parent / "qa/owned-shutdown-tests")
    )
).resolve()
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src")]
import pf_native_control as native  # noqa: E402
from pf_runtime import owned_shutdown as owned  # noqa: E402

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows held process handles")


@pytest.fixture
def case_root() -> Path:
    path = QA / uuid.uuid4().hex
    path.mkdir(parents=True)
    return path


def put(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def save(root: Path, name: str, value: Any) -> None:
    (root / name).write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


@pytest.fixture
def policy(case_root: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Control policy inputs; this fixture never opens or terminates a process."""
    workplace, target, manager = (
        case_root / name for name in ("workplace", "target", "manager")
    )
    workplace.mkdir()
    manager.mkdir()
    script = target / "tools/processforge.py"
    put(script, b"# test-only process entry\n")
    save(
        target,
        "processforge-core.manifest.json",
        {
            "files": [
                {
                    "relative_path": "tools/processforge.py",
                    "sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
                }
            ]
        },
    )
    token = "synthetic-policy-token"
    state: dict[str, Any] = {
        "pid": 43210,
        "instance_id": "fixture-instance",
        "endpoint": "http://127.0.0.1:12345",
        "started_at": "fixture-start",
        "status": "ready",
        "workplace_root": str(workplace),
        "token_hash": "sha256:" + hashlib.sha256(token.encode()).hexdigest(),
    }
    lock = {"pid": state["pid"], "instance_id": state["instance_id"]}
    facts = owned._ProcessFacts(
        state["pid"],
        Path(sys.executable).resolve(),
        123456,
        (
            sys.executable,
            "-B",
            str(script),
            "runtime",
            "serve",
            "--workplace",
            str(workplace),
        ),
    )
    events: list[str] = []
    model = SimpleNamespace(
        root=case_root,
        workplace=workplace,
        target=target,
        manager=manager,
        script=script,
        token=token,
        state=state,
        lock=lock,
        events=events,
        timeout=0.5,
        request_options=[],
        facts=[facts],
        reads=0,
        status_code=200,
        status_mutation=lambda state: state,
        owner_mutation=lambda state, lock, count: (state, lock),
        request_side_effect=lambda: None,
    )

    class Process:
        def __init__(self, pid: int) -> None:
            assert pid == state["pid"]
            events.append("open")

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *args: Any) -> None:
            events.append("close")

        def facts(self) -> Any:
            events.append("facts")
            return model.facts.pop(0) if len(model.facts) > 1 else model.facts[0]

        def terminate(self, expected: Any, timeout: float) -> None:
            assert expected == facts and timeout == model.timeout
            events.append("terminate")

    @contextmanager
    def critical() -> Any:
        events.append("critical-enter")
        try:
            yield
        finally:
            events.append("critical-exit")

    def read_owner() -> Any:
        model.reads += 1
        events.append("read-owner")
        return model.owner_mutation(
            copy.deepcopy(state), copy.deepcopy(lock), model.reads
        )

    def request(method: str, url: str, **options: Any) -> Any:
        events.append("request")
        model.request_options.append(dict(options))
        assert method == "GET" and url == state["endpoint"] + "/status"
        assert options["token"] == token
        model.request_side_effect()
        return model.status_code, model.status_mutation(copy.deepcopy(state))

    model.entry = SimpleNamespace(
        root=manager,
        image=SimpleNamespace(root=manager),
        publication=object(),
        control=None,
    )
    monkeypatch.setattr(native, "current_entry", lambda: model.entry)
    monkeypatch.setattr(owned, "_WindowsProcess", Process)
    model.initial = {"kind": "ready", "matching": True, "state": state, "lock": lock}
    model.invoke = lambda: owned.force_ready_owner_stop(
        workplace,
        model.initial,
        token,
        read_owner=read_owner,
        request=request,
        critical_section=critical,
        timeout=model.timeout,
    )
    return model


def test_policy_rechecks_owner_and_process_under_critical_section(policy: Any) -> None:
    policy.invoke()
    assert policy.events == [
        "open",
        "facts",
        "critical-enter",
        "read-owner",
        "request",
        "facts",
        "read-owner",
        "terminate",
        "critical-exit",
        "close",
    ]


@pytest.mark.parametrize("timeout", [0.5, 45.0])
def test_configured_timeout_reaches_authentication_and_termination(
    policy: Any, timeout: float
) -> None:
    policy.timeout = timeout
    policy.invoke()
    assert policy.request_options == [{"token": policy.token, "timeout": timeout}]
    assert policy.events.count("request") == 1
    assert policy.events.count("terminate") == 1
    assert policy.events[-1] == "close"


@pytest.mark.parametrize("fault", ["no_entry", "unsealed", "no_image", "managed"])
def test_unqualified_caller_never_opens_a_process(policy: Any, fault: str) -> None:
    if fault == "no_entry":
        policy.entry = None
    elif fault == "unsealed":
        policy.entry.publication = None
    elif fault == "no_image":
        policy.entry.image = None
    else:
        policy.entry.control = object()
    with pytest.raises(
        owned.OwnedShutdownError, match="requires_sealed_file_installer"
    ):
        policy.invoke()
    assert policy.events == []


@pytest.mark.parametrize(
    "fault",
    [
        "boolean_pid",
        "self_pid",
        "token",
        "remote_endpoint",
        "wrong_workplace",
        "lock_owner",
        "not_ready",
        "no_start",
    ],
)
def test_unqualified_owner_never_opens_a_process(policy: Any, fault: str) -> None:
    if fault == "boolean_pid":
        policy.state["pid"] = True
    elif fault == "self_pid":
        policy.state["pid"] = os.getpid()
        policy.lock["pid"] = os.getpid()
    elif fault == "token":
        policy.state["token_hash"] = "sha256:" + "0" * 64
    elif fault == "remote_endpoint":
        policy.state["endpoint"] = "http://example.invalid:12345"
    elif fault == "wrong_workplace":
        policy.state["workplace_root"] = str(policy.target)
    elif fault == "lock_owner":
        policy.lock["instance_id"] = "other-owner"
    elif fault == "not_ready":
        policy.state["status"] = "stale"
    else:
        policy.state["started_at"] = ""
    with pytest.raises(owned.OwnedShutdownError):
        policy.invoke()
    assert policy.events == []


@pytest.mark.parametrize(
    "fault",
    [
        "first_owner",
        "last_owner",
        "status_owner",
        "authentication",
        "process_creation",
        "manifest",
        "managed_target",
        "same_root",
    ],
)
def test_revalidation_failure_never_terminates_policy_process(
    policy: Any, fault: str
) -> None:
    if fault in {"first_owner", "last_owner"}:
        target_read = 1 if fault == "first_owner" else 2

        def mutate(state: dict[str, Any], lock: dict[str, Any], count: int) -> Any:
            if count == target_read:
                lock["instance_id"] = "new-owner"
            return state, lock

        policy.owner_mutation = mutate
    elif fault == "status_owner":
        policy.status_mutation = lambda state: {**state, "instance_id": "new-owner"}
    elif fault == "authentication":
        policy.status_code = 403
    elif fault == "process_creation":
        policy.facts.append(replace(policy.facts[0], creation=123457))
    elif fault == "manifest":
        policy.request_side_effect = lambda: policy.script.write_bytes(
            b"replaced entry\n"
        )
    elif fault == "managed_target":
        policy.request_side_effect = lambda: (
            policy.target / "runtime/native-control"
        ).mkdir(parents=True)
    else:
        policy.entry.root = policy.target
        policy.entry.image.root = policy.target
    with pytest.raises(owned.OwnedShutdownError):
        policy.invoke()
    assert "terminate" not in policy.events
    assert policy.events[-1] == "close"


def test_real_windows_handle_identity_mismatch_does_not_signal_controlled_child(
    case_root: Path,
) -> None:
    script = case_root / "wait.py"
    script.write_text(
        "import os,sys; print(os.getpid(),flush=True); sys.stdin.readline()\n",
        encoding="utf-8",
    )
    command = [BASE_PYTHON, "-B", str(script), "fixture", "extra"]
    child = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout is not None
        actual_pid = int(child.stdout.readline())
        with owned._WindowsProcess(actual_pid) as process:
            facts = process.facts()
            assert facts.pid == actual_pid and facts.creation > 0
            assert facts.image == Path(BASE_PYTHON).resolve()
            assert facts.arguments[2:] == (str(script), "fixture", "extra")
            with pytest.raises(owned.OwnedShutdownError, match="identity_changed"):
                process.terminate(replace(facts, creation=facts.creation + 1), 0.1)
            assert process.alive() and child.poll() is None
            process.terminate(facts, 3.0)
            assert not process.alive()
            with pytest.raises(owned.OwnedShutdownError, match="process_exited"):
                process.terminate(facts, 0.1)
        assert process.handle is None
        assert child.wait(timeout=5) == 1
        save(
            case_root,
            "handle-result.json",
            {
                "command": command,
                "pid": facts.pid,
                "creation": facts.creation,
                "image": facts.image,
                "wrong_creation_preserved_live_child": True,
                "exact_handle_terminated_only_controlled_child": True,
                "original_popen_handle_retained_through_exit": True,
            },
        )
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)


CONTROLLED_SERVER = r"""
import argparse,hashlib,json,os
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
parser=argparse.ArgumentParser();parser.add_argument('command');parser.add_argument('operation');parser.add_argument('--workplace');args=parser.parse_args()
workplace=Path(args.workplace)
config=json.loads((workplace/'fixture-input.json').read_text())
token=config['token']
state={}
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,code,body):
        raw=json.dumps(body).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/readyz':return self.reply(200,{'ready':True})
        if self.headers.get('Authorization')!='Bearer '+token:return self.reply(401,{})
        self.reply(200,state)
    def do_POST(self):
        if self.headers.get('Authorization')!='Bearer '+token:return self.reply(401,{})
        self.reply(409,{'error':'runtime_busy_or_activity_unknown'})
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
state.update(pid=os.getpid(),instance_id='controlled-fixture-owner',endpoint='http://127.0.0.1:'+str(server.server_port),started_at='controlled-fixture-start',status='ready',workplace_root=str(workplace.resolve()),token_hash='sha256:'+hashlib.sha256(token.encode()).hexdigest(),capabilities={'guarded_shutdown':1})
for name,value in [('service.json',state),('runtime.lock',{'pid':os.getpid(),'instance_id':state['instance_id']}),('token.json',{'token':token})]:
    (workplace/'runtime/pf-runtime'/name).write_text(json.dumps(value))
print(json.dumps({'ready':True,'pid':os.getpid()}),flush=True)
server.serve_forever()
"""


def test_actual_external_sealed_force_stops_only_controlled_ready_owner(
    case_root: Path,
) -> None:
    manager = case_root / "manager"
    payload = {
        path.relative_to(ROOT).as_posix(): native.canonical_release_bytes(
            path.read_bytes()
        )
        for directory in ("src", "tools")
        for path in (ROOT / directory).rglob("*.py")
    }
    payload.update({native.INVENTORY: b"", "VERSION": b"fixture\n"})
    candidate = native.build_publication(
        payload, version="1.0.0", source={"fixture": True}, generated_at="fixture"
    )
    for relative, raw in {
        **candidate.payload,
        native.MANIFEST: candidate.manifest,
    }.items():
        put(manager / relative, raw)
    script = case_root / "target/tools/processforge.py"
    put(script, textwrap.dedent(CONTROLLED_SERVER).encode())
    save(
        script.parents[1],
        "processforge-core.manifest.json",
        {
            "schema_version": 1,
            "files": [
                {
                    "relative_path": "tools/processforge.py",
                    "sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
                }
            ],
        },
    )
    workplace = case_root / "workplace"
    (workplace / "runtime/pf-runtime").mkdir(parents=True)
    save(workplace, "fixture-input.json", {"token": "synthetic-controlled-child-token"})
    command = [
        BASE_PYTHON,
        "-B",
        str(script),
        "runtime",
        "serve",
        "--workplace",
        str(workplace),
    ]
    child = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    try:
        assert child.stdout is not None
        ready = json.loads(child.stdout.readline())
        assert ready["ready"]
        controller = case_root / "controller.py"
        controller.write_text(
            textwrap.dedent("""
            import argparse,json,sys,types
            from pathlib import Path
            from types import SimpleNamespace
            manager,workplace,case=map(Path,sys.argv[1:])
            leaf=(manager/'tools/pf_native_control.py').read_bytes()
            native=types.ModuleType('pf_native_control');native.__file__=str(manager/'tools/pf_native_control.py');native._captured_source=leaf
            sys.modules['pf_native_control']=native
            exec(compile(leaf,native.__file__,'exec',dont_inherit=True),native.__dict__)
            entry=native.bootstrap_entry(manager,trusted_leaf=leaf)
            assert entry.control is None and entry.publication is not None and entry.image is not None
            sys.path[:0]=[str(manager/'tools'),str(manager/'src')]
            from pf_runtime import service,owned_shutdown
            core=SimpleNamespace(resolve_workplace_root=lambda value:workplace)
            initial=service.inspect_lifecycle(workplace,core)
            assert initial['kind']=='ready' and initial['matching']
            with owned_shutdown._WindowsProcess(initial['state']['pid']) as retained:
                facts=retained.facts()
                args=argparse.Namespace(command='server',force=False,workplace=str(workplace),timeout=3.0)
                try:service.command_stop(args,core)
                except SystemExit as error:assert '409' in str(error)
                else:raise AssertionError('guarded 409 must refuse')
                assert retained.alive()
                args.force=True
                assert service.command_stop(args,core)==0
                assert not retained.alive()
                result={'guarded_409_preserves_live_owner':True,'explicit_force_stops_exact_controlled_owner':True,'pid':facts.pid,'creation':facts.creation,'image':str(facts.image),'arguments':facts.arguments,'caller_publication':entry.publication.manifest_sha256,'owner_pinned_handle_retained_through_exit':True,'state_after':service.read_json(service.service_path(workplace)),'lock_removed':not service.lock_path(workplace).exists()}
                (case/'sealed-force-result.json').write_text(json.dumps(result,indent=2))
                print(json.dumps(result,sort_keys=True))
            """),
            encoding="utf-8",
        )
        controller_command = [
            BASE_PYTHON,
            "-I",
            "-B",
            str(controller),
            str(manager),
            str(workplace),
            str(case_root),
        ]
        result = subprocess.run(
            controller_command,
            cwd=case_root,
            capture_output=True,
            text=True,
            timeout=35,
            check=False,
        )
        (case_root / "controller.stdout.log").write_text(
            result.stdout, encoding="utf-8"
        )
        (case_root / "controller.stderr.log").write_text(
            result.stderr, encoding="utf-8"
        )
        save(
            case_root,
            "controller.command.json",
            {
                "command": controller_command,
                "exit_code": result.returncode,
                "controlled_child_command": command,
            },
        )
        assert result.returncode == 0, result.stdout + result.stderr
        receipt = json.loads((case_root / "sealed-force-result.json").read_text())
        assert receipt["pid"] == ready["pid"]
        assert receipt["lock_removed"]
        assert receipt["state_after"]["status"] == "stale"
        assert child.wait(timeout=5) == 1
        assert not (script.parents[1] / "runtime/native-control").exists()
        assert not (script.parents[1] / "runtime/managed-ingress").exists()
    finally:
        if child.poll() is None:
            child.kill()
        stdout, stderr = child.communicate(timeout=5)
        (case_root / "child.stdout.log").write_text(stdout, encoding="utf-8")
        (case_root / "child.stderr.log").write_text(stderr, encoding="utf-8")
