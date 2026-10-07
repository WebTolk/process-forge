"""Operator CLI integration with actual pinned Work authority."""
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
import time

from ..work.context import validate_execution_contract
from .contracts import (EgressError, binding_for, bounded_json, digest, encoded,
                        fingerprint, require_v2, security_intent, validate_policy)
from .engine import Session
from .storage import Store
from .transport import JsonTransport, implementation_id
from .windows import no_reparse, read_source, verify_private


def policy_file(path):
    return validate_policy(bounded_json(read_source(Path(path).absolute(), 1048576), 1048576))


def work_session(core, *, project, assignment_id, attempt, policy_path, store_root, credential_path=None):
    assignment_path = core.assignment_yaml_path(project, assignment_id)
    capsule_path = core.assignment_capsule_path(project, assignment_id)
    initial_stage = None

    def current():
        task = core.load_yaml_document(assignment_path)
        capsule = core.load_yaml_document(capsule_path)
        contract = capsule.get("execution_contract") or {}
        require_v2(contract)
        result = validate_execution_contract(project, assignment_path, task, capsule, core, require_ready=True)
        if result.get("status") != "valid":
            raise EgressError("work_authority_changed")
        run = core.load_run(project, task["run_id"])
        if task.get("status") != "in_progress" or run.get("status") not in {"active", "in_progress"}:
            raise EgressError("work_authority_changed")
        if initial_stage is not None and task.get("stage") != initial_stage:
            raise EgressError("invalid_binding")
        return task, contract

    task, contract = current()
    initial_stage = task["stage"]

    def authority():
        task, contract = current()
        return {**contract["identity"], "contract_checksum": contract["contract_checksum"], "stage": task["stage"], "attempt": attempt}

    @contextmanager
    def authority_lock():
        # Same OS guard as ProcessExecutionService.transition. A stage cannot
        # change between final authorization, durable reservation and disclosure.
        run_path = core.locate_flow_root(project) / "runs" / task["run_id"] / "run.yaml"
        try:
            with core.registry_file_lock(run_path, timeout_seconds=0.1, stale_after_seconds=0):
                yield
        except SystemExit:
            raise EgressError("work_authority_busy") from None

    loader = lambda: policy_file(policy_path)
    credential = None
    if credential_path:
        credential_file = Path(credential_path).absolute()
        verify_private(credential_file)
        try:
            credential = read_source(credential_file, 4096).decode("ascii").strip()
        except UnicodeError:
            raise EgressError("credential_channel_invalid") from None
    policy = loader()
    return Session(project=project, contract=contract, stage=initial_stage, attempt=attempt, policy_loader=loader,
                   authority=authority, store=Store(store_root, project),
                   transport=JsonTransport(policy["recipient"], credential=credential), authority_lock=authority_lock)


def qualify(core_root: Path, store: Store):
    """Operator-only local qualification; never executes a model or sends project data."""
    before = implementation_id()
    report = []
    for script in ("smoke_egress_engine.py", "smoke_egress_work.py", "smoke_egress_transport.py"):
        result = subprocess.run([sys.executable, "-B", str(core_root / "tools" / script), "--json"],
                                cwd=core_root, capture_output=True, timeout=300)
        if result.returncode or len(result.stdout) > 1048576:
            raise EgressError("qualification_failed")
        data = bounded_json(result.stdout, 1048576)
        if data.get("status") != "passed":
            raise EgressError("qualification_failed")
        report.append({"script": script, "report_checksum": digest(result.stdout), "checks": data["checks"]})
    if implementation_id() != before:
        raise EgressError("qualification_changed")
    evidence = {"status": "passed", "implementation": before, "time": int(time.time()),
                "route": "managed-http-json-v1", "reports": report}
    with store.locked():
        store.write("qualification.json", evidence)
    return {"status": "passed", "implementation": before, "checks": sum(x["checks"] for x in report)}


def command(args, core):
    try:
        action = args.egress_command
        project = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else None
        if action == "bind":
            policy = policy_file(args.policy)
            intent = {"egress": binding_for(policy), "allowed_read_files": sorted(policy["sources"])}
            if args.predecessor:
                if project is None:
                    raise EgressError("project_required")
                previous = core.assignment_capsule_path(project, args.predecessor)
                intent["predecessor"] = {"assignment_id": args.predecessor, "capsule_checksum": digest(read_source(previous, 2097152))}
            payload = security_intent(intent)
        elif action in {"run", "export"}:
            session = work_session(core, project=project, assignment_id=args.assignment, attempt=args.attempt,
                                   policy_path=args.policy, store_root=Path(args.store_root), credential_path=getattr(args, "credential_file", None))
            try:
                if action == "run":
                    payload = session.run(args.rounds)
                else:
                    output = Path(args.output).absolute()
                    no_reparse(output.parent)
                    if output.exists():
                        raise EgressError("export_exists")
                    view = session.prepare_view()
                    raw = session.export_view(view)
                    with output.open("xb") as stream:
                        stream.write(raw)
                        stream.flush()
                        import os
                        os.fsync(stream.fileno())
                    payload = {"status": "exported", "bytes": len(raw)}
            finally:
                session.close()
        else:
            store = Store(Path(args.store_root), project)
            if action == "qualify":
                payload = qualify(Path(core.__file__).resolve().parents[1], store)
            elif action == "revoke":
                store.revoke(binding_for(policy_file(args.policy)))
                payload = {"status": "revoked"}
            elif action == "status":
                with store.locked():
                    qualification = store.load("qualification.json", {})
                payload = {"status": "qualified" if qualification.get("implementation") == implementation_id()
                           and qualification.get("status") == "passed" else "unqualified",
                           "native_routes": "unsupported", "isolated_local": "unsupported"}
            elif action == "prune":
                payload = {"status": "pruned", "expired_receipts": store.prune()}
            else:
                raise EgressError("operation_unsupported")
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0
    except (EgressError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "blocked", "reason": exc.code if isinstance(exc, EgressError) else "egress_operation_failed"}))
        return 1


def add_parser(sub, core):
    parser = sub.add_parser("egress", help="Qualify and operate explicit v2 managed disclosure mediation.")
    commands = parser.add_subparsers(dest="egress_command", required=True)
    for name in ("bind", "qualify", "status", "run", "export", "revoke", "prune"):
        item = commands.add_parser(name)
        item.set_defaults(func=lambda args: command(args, core))
        item.add_argument("--project-root", required=name != "bind")
        if name in {"bind", "run", "export", "revoke"}:
            item.add_argument("--policy", required=True, help="Trusted local operator policy JSON.")
        if name != "bind":
            item.add_argument("--store-root", required=True, help="External owner-only .pf-egress-private directory.")
        if name == "bind":
            item.add_argument("--predecessor", help="Preserved predecessor assignment id; requires project root.")
        if name in {"run", "export"}:
            item.add_argument("--assignment", required=True)
            item.add_argument("--attempt", type=int, required=True)
        if name == "run":
            item.add_argument("--rounds", type=int, default=16)
            item.add_argument("--credential-file", help="Owner-only transport credential, never model input.")
        if name == "export":
            item.add_argument("--output", required=True, help="New derivative; existing files are never replaced.")
