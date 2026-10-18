from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
path = ROOT / 'tools/processforge.py'
text = path.read_text(encoding='utf-8')
anchor = '''    capsule = load_yaml_document(capsule_path)
    capsule_meta = capsule.get("capsule") if isinstance(capsule, dict) else {}
    recorded_checksum ='''
replacement = '''    capsule = load_yaml_document(capsule_path)
    if isinstance(capsule, dict) and "execution_contract" in capsule:
        from processforge_core.work_context import validate_execution_contract
        assignment_path = assignment_yaml_path(project_root, task_id)
        metadata = extract_assignment_front_matter(assignment_path) if assignment_path.is_file() else {}
        validation = validate_execution_contract(project_root, assignment_path, metadata, capsule, sys.modules[__name__])
        return ("fresh" if validation["status"] == "valid" else "stale"), rel(capsule_path, project_root)
    capsule_meta = capsule.get("capsule") if isinstance(capsule, dict) else {}
    recorded_checksum ='''
assert text.count(anchor) == 1
text = text.replace(anchor, replacement)
anchor = '''    task = load_task(project_root, task_id)
    workspace_access_path = write_workspace_access_runtime_file(project_root, task)'''
replacement = '''    task = load_task(project_root, task_id)
    from processforge_core.work_context import validate_execution_contract
    prepared_capsule = load_yaml_document(assignment_capsule_path(project_root, task_id))
    validation = validate_execution_contract(project_root, assignment_yaml_path(project_root, task_id), task,
                                             prepared_capsule, sys.modules[__name__], require_ready=True)
    if validation["status"] != "valid":
        raise SystemExit("FAIL: " + str(validation.get("reason") or "execution_contract_invalid") + "; create_successor_work")
    workspace_access_path = write_workspace_access_runtime_file(project_root, task)'''
assert text.count(anchor) == 1
text = text.replace(anchor, replacement)
text = text.replace('create a new capsule intentionally before launch', 'create_successor_work; immutable contexts cannot be rebuilt in place')
anchor = '''    return print_checks(checks)


RUN_STATUSES ='''
replacement = '''    if "execution_contract" in capsule:
        from processforge_core.work_context import validate_execution_contract
        assignment_ref = str(capsule.get("capsule", {}).get("assignment_path") or "")
        assignment_path = project_root / assignment_ref
        metadata = extract_assignment_front_matter(assignment_path) if assignment_path.is_file() else {}
        result = validate_execution_contract(project_root, assignment_path, metadata, capsule, sys.modules[__name__])
        checks.append(check("PASS" if result["status"] == "valid" else "FAIL", "execution contract: " + str(result.get("reason") or result["status"])))
        if result.get("readiness", {}).get("status") == "blocked":
            checks.append(check("WARN", "worker readiness: " + ", ".join(item["code"] for item in result["readiness"]["blockers"])))
    else:
        checks.append(check("WARN", "legacy_contract_incomplete: create_successor_work for restricted execution"))
    return print_checks(checks)


RUN_STATUSES ='''
assert text.count(anchor) == 1
text = text.replace(anchor, replacement)
path.write_text(text, encoding='utf-8')

path = ROOT / 'src/processforge_core/process_execution.py'
text = path.read_text(encoding='utf-8')
anchor = '''        blockers = [copy.deepcopy(item) for item in stored_blockers if isinstance(item, dict)]
        if str(assignment.get("stage_status")'''
replacement = '''        blockers = [copy.deepcopy(item) for item in stored_blockers if isinstance(item, dict)]
        contract_validation = self._contract_validation(assignment)
        if contract_validation.get("status") == "blocked":
            blockers.append({"code": contract_validation.get("reason") or "execution_contract_invalid"})
        if str(assignment.get("stage_status")'''
assert text.count(anchor) == 1
text = text.replace(anchor, replacement)
anchor = '''                        "identity_source": "assignment_process_pin"},'''
replacement = '''                        "identity_source": "assignment_process_pin", "validation": contract_validation},'''
assert text.count(anchor) == 1
text = text.replace(anchor, replacement)
anchor = '''            pending_intent, intent_error = self._load_completion_intent(run, assignment)'''
replacement = '''            contract_validation = self._contract_validation(assignment)
            if contract_validation.get("status") == "blocked":
                return self._blocked(contract_validation.get("reason") or "execution_contract_invalid", remediation="create_successor_work")
            pending_intent, intent_error = self._load_completion_intent(run, assignment)'''
assert text.count(anchor) == 1
text = text.replace(anchor, replacement)
anchor = '    def _write_capsule('
replacement = '''    def _contract_validation(self, assignment: dict[str, Any]) -> dict[str, Any]:
        from .work_context import validate_execution_contract

        path = self._flow_root() / "contexts" / "assignment-capsules" / f"{assignment['id']}.capsule.yaml"
        if not path.is_file():
            return {"status": "blocked", "reason": "work_context_unavailable"}
        try:
            if path.stat().st_size > 2 * 1024 * 1024:
                return {"status": "blocked", "reason": "execution_contract_invalid"}
            capsule = self.core.load_yaml_document(path)
            if "execution_contract" not in capsule:
                return {"status": "legacy", "reason": "legacy_contract_incomplete"}
            expected = (assignment.get("process_execution") or {}).get("assignment_capsule_checksum")
            if expected != "sha256:" + self._sha256_file(path):
                return {"status": "blocked", "reason": "immutable_context_changed"}
            return validate_execution_contract(self.project_root, self._assignment_path(assignment["id"]), assignment, capsule, self.core, check_sources=False)
        except (OSError, ValueError, TypeError, AttributeError):
            return {"status": "blocked", "reason": "execution_contract_invalid"}

    def _write_capsule('''
assert text.count(anchor) == 1
text = text.replace(anchor, replacement)
path.write_text(text, encoding='utf-8')
print('Integrated complete-contract intent validation and immutable reuse policy')
