from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
path=ROOT/'tools/pf_runtime/host.py'
text=path.read_text(encoding='utf-8')
text=text.replace('import os\n','import os\nimport re\n',1)
text=text.replace('from . import RUNTIME_PROTOCOL_VERSION\n','from . import RUNTIME_PROTOCOL_VERSION\nfrom .provider_adapters import AdapterRegistry, WorkerBinding, worker_input_summary\nfrom .builtin_provider_adapters import DEFAULT_ADAPTER_REGISTRY\n',1)
text=text.replace('"adapter": str(source.get("adapter") or raw.get("adapter") or "runtime-legacy"),','"adapter": "runtime-legacy",',1)
start=text.index('def _is_worker_conversation(')
end=text.index('\ndef _pending_conversation_key',start)
text=text[:start]+'''def _adapter_admission(envelope: dict[str, Any], project_root: Path, core: Any,
                       registry: AdapterRegistry = DEFAULT_ADAPTER_REGISTRY) -> str:
    policy = registry.resolve(envelope)
    if policy is None:
        return "adapter_untrusted"
    try:
        if not policy.validate(envelope):
            return "provenance_rejected"
        session = str(envelope.get("source_session_id") or "")
        derived = envelope.get("derived_event")
        if derived is not None:
            if not isinstance(derived, dict):
                return "provenance_rejected"
            derived_ref = str(derived.get("project_root") or derived.get("cwd") or "")
            if derived_ref and resolve_project(derived_ref, core) != project_root:
                raise PermissionError("derived event project_root does not match native envelope")
            source = derived.get("source") or {}
            if not isinstance(source, dict):
                return "provenance_rejected"
            # Every supplied session spelling must agree, not only the first.
            if any(str(value) != session for value in (source.get("session_id"), derived.get("session_id")) if value):
                return "provenance_rejected"
        messages = envelope.get("derived_conversation_messages")
        if messages is not None:
            if not isinstance(messages, list) or len(messages) > 128:
                return "provenance_rejected"
            for item in messages:
                if not isinstance(item, dict):
                    return "provenance_rejected"
                source = item.get("content_source") or {}
                if not isinstance(source, dict) or str(item.get("session_id") or session) != session:
                    return "provenance_rejected"
                for key in ("provider", "adapter", "native_event_type"):
                    if key in source and source[key] != envelope.get(key):
                        return "provenance_rejected"
                if not policy.allows_message(envelope, item):
                    return "provenance_rejected"
    except (ValueError, TypeError, KeyError, OSError, UnicodeError):
        return "provenance_rejected"
    return ""


def _is_worker_conversation(envelope: dict[str, Any], registry: AdapterRegistry = DEFAULT_ADAPTER_REGISTRY) -> bool:
    policy = registry.resolve(envelope)
    return policy is not None and policy.session_mode == "worker"

''' +text[end:]
text=text.replace('project_root: Path, workplace_root: Path, session_id: str, core: Any\n)', 'project_root: Path, workplace_root: Path, session_id: str, core: Any,\n    registry: AdapterRegistry = DEFAULT_ADAPTER_REGISTRY,\n)',1)
text=text.replace('_conversation_messages(envelope, receipt, project_root, workplace_root, core)', '_conversation_messages(envelope, receipt, project_root, workplace_root, core, registry=registry)',1)
start=text.index('def worker_input_summary(')
end=text.index('\ndef _conversation_messages(',start)
text=text[:start]+'''def _worker_input_contract(binding: WorkerBinding, project_root: Path, core: Any) -> dict[str, Any] | None:
    contract_path = project_root / ".pf" / "runtime" / "agent-runs" / binding.run_id / binding.task_id / "worker-input-contract.json"
    try:
        if not contract_path.resolve().is_relative_to(project_root.resolve()) or contract_path.is_symlink() or contract_path.stat().st_size > 2 * 1024 * 1024:
            return None
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return None
    required = {"run_id": binding.run_id, "task_id": binding.task_id, "attempt": binding.attempt,
                "stdin_payload_hash": binding.content_hash, "expected_report": binding.expected_report, "summary": binding.summary}
    return required if isinstance(contract, dict) and all(str(contract.get(key) or "") == value for key, value in required.items()) else None


def _allowed_conversation_message(envelope: dict[str, Any], item: dict[str, Any], registry: AdapterRegistry = DEFAULT_ADAPTER_REGISTRY) -> bool:
    policy = registry.resolve(envelope)
    return policy is not None and policy.allows_message(envelope, item)


def _worker_session_authorized(envelope: dict[str, Any], project_root: Path, core: Any,
                               registry: AdapterRegistry = DEFAULT_ADAPTER_REGISTRY) -> bool:
    policy = registry.resolve(envelope)
    binding = policy.worker_binding(envelope) if policy is not None else None
    if not isinstance(binding, WorkerBinding) or binding.category not in {"input", "output"}:
        return False
    if not all(re.fullmatch(r"[a-z0-9]+(?:-+[a-z0-9]+)*", value) for value in (binding.run_id, binding.task_id)) or not re.fullmatch(r"[0-9]+", binding.attempt):
        return False
    if str(envelope.get("source_session_id") or "") != binding.session_id:
        return False
    if binding.content_hash != "sha256:" + hashlib.sha256(binding.content.encode("utf-8")).hexdigest():
        return False
    try:
        task = core.load_task(project_root, binding.task_id)
        if str(task.get("run_id") or "") != binding.run_id:
            return False
        state = core.load_agent_run_state(project_root, binding.run_id, binding.task_id)
        if not state or binding.attempt != str(state.get("attempt") or ""):
            return False
        expected_report = core.expected_report_artifact(task)
        if not expected_report or binding.expected_report != expected_report:
            return False
        report = core.project_output_path(project_root, expected_report)
        if binding.category == "input":
            return _worker_input_contract(binding, project_root, core) is not None
        return report.is_file() and report.read_text(encoding="utf-8", errors="replace") == binding.content
    except (OSError, ValueError, TypeError, UnicodeError, SystemExit):
        return False


def _is_session_end_fallback_duplicate(envelope: dict[str, Any], item: dict[str, Any], project_root: Path, core: Any,
                                      registry: AdapterRegistry = DEFAULT_ADAPTER_REGISTRY) -> bool:
    policy = registry.resolve(envelope)
    identifiers, types = policy.fallback_participants(envelope, item) if policy else ((), ())
    if not identifiers and not types:
        return False
    content = item.get("content")
    turn_id = str(item.get("turn_id") or "")
    session_id = str(envelope.get("source_session_id") or "")
    if not isinstance(content, str) or not content.strip() or not session_id:
        return False
    for existing in core.load_chat_messages(project_root, session_id):
        body = existing.get("message") if isinstance(existing.get("message"), dict) else {}
        participant = existing.get("participant") if isinstance(existing.get("participant"), dict) else {}
        existing_primary = str(participant.get("id") or "") in identifiers or str(participant.get("type") or "") in types
        if ((not turn_id or str(existing.get("turn_id") or "") == turn_id)
                and existing_primary and body.get("role") == "assistant" and body.get("content") == content):
            return True
    return False

''' +text[end:]
text=text.replace('ended_session_presence: dict[str, Any] | None = None,\n)', 'ended_session_presence: dict[str, Any] | None = None,\n    registry: AdapterRegistry = DEFAULT_ADAPTER_REGISTRY,\n)',1)
text=text.replace('    messages = envelope.get("derived_conversation_messages")\n    if messages is None:', '    reason = _adapter_admission(envelope, project_root, core, registry)\n    if reason:\n        return _conversation_denial(reason)\n    policy = registry.resolve(envelope)\n    messages = envelope.get("derived_conversation_messages")\n    if messages is None:',1)
text=text.replace('is_worker = _is_worker_conversation(envelope)', 'is_worker = _is_worker_conversation(envelope, registry)',1)
text=text.replace('_worker_session_authorized(envelope, project_root, core)', '_worker_session_authorized(envelope, project_root, core, registry)',1)
text=text.replace('_allowed_conversation_message(envelope, item):','_allowed_conversation_message(envelope, item, registry):',1)
text=text.replace('_is_session_end_fallback_duplicate(envelope, item, project_root, core):','_is_session_end_fallback_duplicate(envelope, item, project_root, core, registry):',1)
text=text.replace('owned_report = is_worker and str(envelope.get("native_event_type") or "") == "WorkerExpectedReportCaptured"','owned_report = is_worker and policy is not None and policy.owns_report(envelope, item)',1)
text=text.replace('*, project_ref: str | None = None) -> dict[str, Any]:\n    from processforge_core import diagnostics', '*, project_ref: str | None = None, registry: AdapterRegistry = DEFAULT_ADAPTER_REGISTRY) -> dict[str, Any]:\n    from processforge_core import diagnostics',1)
text=text.replace('_ingest_event(raw, workplace_root, core, project_ref=project_ref)', '_ingest_event(raw, workplace_root, core, project_ref=project_ref, registry=registry)',1)
text=text.replace('def _ingest_event(raw: dict[str, Any], workplace_root: Path | None, core: Any, *, project_ref: str | None = None)', 'def _ingest_event(raw: dict[str, Any], workplace_root: Path | None, core: Any, *, project_ref: str | None = None, registry: AdapterRegistry = DEFAULT_ADAPTER_REGISTRY)',1)
text=text.replace('    if not receipt.accepted:\n        return response\n\n    derived =', '    if not receipt.accepted:\n        return response\n    reason = _adapter_admission(envelope, project_root, core, registry)\n    if reason:\n        return {**response, "routing_status": "denied", "diagnostics": {**response["diagnostics"], "adapter": {"status": "denied", "reason": reason}, "conversation": {"status": "denied", "reason": reason}}}\n\n    derived =',1)
text=text.replace('_flush_deferred_conversation(project_root, workplace_root, derived_session_id, core)', '_flush_deferred_conversation(project_root, workplace_root, derived_session_id, core, registry)',1)
text=text.replace('ended_session_presence=ended_session_presence,\n    )', 'ended_session_presence=ended_session_presence,\n        registry=registry,\n    )',1)
text=text.replace('and not _is_worker_conversation(envelope)\n', 'and not _is_worker_conversation(envelope, registry)\n',1)
path.write_text(text,encoding='utf-8',newline='\n')
print('Host extraction integrated')
