from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
path = ROOT / 'tools/processforge.py'
text = path.read_text(encoding='utf-8')
start = text.index('def normalized_assignment_contract(')
end = text.index('\n\nWORKSPACE_ACCESS_KEYS', start)
text = text[:start] + '''def normalized_assignment_contract(project_root: Path, assignment: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    from processforge_core.work_context import normalized_assignment_contract as normalize
    return normalize(project_root, assignment, metadata, sys.modules[__name__])
''' + text[end:]
anchor = '''    assn_id = safe_id(str(metadata.get("id", assignment.stem)), "assignment")
    required ='''
replacement = '''    assn_id = safe_id(str(metadata.get("id", assignment.stem)), "assignment")
    capsule_path = locate_flow_root(project_root) / "contexts" / "assignment-capsules" / f"{assn_id}.capsule.yaml"
    if capsule_path.exists():
        raise SystemExit("FAIL: immutable_context_exists; create_successor_work; --force cannot replace a pinned capsule")
    if (metadata.get("process_execution") or {}).get("assignment_capsule"):
        raise SystemExit("FAIL: pinned_context_unavailable; create_successor_work or restore the exact recorded context")
    required ='''
assert text.count(anchor) == 1
text = text.replace(anchor, replacement)
anchor = '''    contract = normalized_assignment_contract(project_root, assignment, metadata)
    workspace_access_issues ='''
replacement = '''    from processforge_core.work_context import ContextContractError, build_context_fields
    try:
        fields = build_context_fields(project_root, assignment, metadata, snapshot, sys.modules[__name__],
            workplace=(resolve_project_workplace_manifest(project_root).parent if resolve_project_workplace_manifest(project_root) else None))
    except ContextContractError as exc:
        prefix = "workspace access must use public refs: " if exc.code == "private_path_forbidden" else ""
        raise SystemExit("FAIL: " + prefix + exc.code) from exc
    contract = fields
    workspace_access_issues ='''
assert text.count(anchor) == 1
text = text.replace(anchor, replacement)
anchor = '''    capsule_dir = flow_root / "contexts" / "assignment-capsules"
    capsule_dir.mkdir(parents=True, exist_ok=True)
    capsule_path = capsule_dir / f"{assn_id}.capsule.yaml"
    if capsule_path.exists() and not args.force:
        raise SystemExit(f"FAIL: capsule already exists: {rel(capsule_path, project_root)}")
    capsule_path.write_text(ensure_trailing_newline(dump_yaml(capsule)), encoding="utf-8")'''
replacement = '''    common_context = {**capsule["context"], **fields["context"]}
    capsule.update(fields)
    capsule["context"] = common_context
    capsule["required_capabilities"] = fields["capabilities"]["required"]
    capsule["optional_capabilities"] = fields["capabilities"]["optional"]
    capsule_dir = flow_root / "contexts" / "assignment-capsules"
    capsule_dir.mkdir(parents=True, exist_ok=True)
    capsule_path = capsule_dir / f"{assn_id}.capsule.yaml"
    try:
        with capsule_path.open("x", encoding="utf-8") as stream:
            stream.write(ensure_trailing_newline(dump_yaml(capsule)))
    except FileExistsError as exc:
        raise SystemExit("FAIL: immutable_context_exists; create_successor_work") from exc'''
assert text.count(anchor) == 1
text = text.replace(anchor, replacement)
path.write_text(text, encoding='utf-8')

path = ROOT / 'src/processforge_core/process_execution.py'
text = path.read_text(encoding='utf-8')
start = text.index('    def _write_capsule(')
end = text.index('    def _write_projection(', start)
text = text[:start] + '''    def _write_capsule(self, run: dict[str, Any], assignment: dict[str, Any], pin: dict[str, Any]) -> tuple[str, str]:
        from .work_context import ContextContractError, build_context_fields

        path = self._flow_root() / "contexts" / "assignment-capsules" / f"{assignment['id']}.capsule.yaml"
        if path.exists():
            raise ContextContractError("immutable_context_exists", remediation="create_successor_work")
        snapshot = self.core.load_yaml_document(self._flow_root() / "contexts" / "project-context.snapshot.yaml")
        fields = build_context_fields(self.project_root, self._assignment_path(assignment["id"]), assignment,
                                      snapshot, self.core, workplace=self.workplace_root, pin=pin)
        capsule = {
            "schema_version": 1,
            "capsule": {"id": f"{assignment['id']}-capsule", "generated_at": self.core.now_utc(), "assignment_id": assignment["id"], "assignment_path": f".pf/assignments/{assignment['id']}.yaml", "immutable": True, "worker_may_rebuild_context": False},
            "context_snapshot": {"id": pin["snapshot_id"], "sha256": pin["snapshot_checksum"], "freshness_at_creation": "fresh"},
            **fields,
        }
        capsule["context"].update(freshness="fresh", selected_specializations=_stable_ids(assignment.get("selected_specializations")), applied_project_overrides=[])
        capsule["assignment"]["stage"] = assignment["stage"]
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(self.core.ensure_trailing_newline(self.core.dump_yaml(capsule)))
        except FileExistsError as exc:
            raise ContextContractError("immutable_context_exists", remediation="create_successor_work") from exc
        return self.core.rel(path, self.project_root), "sha256:" + self._sha256_file(path)

''' + text[end:]
anchor = '        capsule_path, capsule_checksum = self._write_capsule(run, assignment, pin)'
replacement = '''        from .work_context import ContextContractError
        try:
            capsule_path, capsule_checksum = self._write_capsule(run, assignment, pin)
        except ContextContractError as exc:
            return self._blocked(exc.code, **exc.details)'''
assert text.count(anchor) == 1
text = text.replace(anchor, replacement)
path.write_text(text, encoding='utf-8')
print('Integrated both builders through common module')
