# Quality Audit Process Authoring Example

Create the example process from prepared answers:

```bash
python bin/pf.py process-create --project-root <project-root> --answers examples/process-authoring/quality-audit/answers.yaml --apply
python bin/pf.py process-doctor --project-root <project-root> --process quality-audit
```

Expected public outputs:

- `processes/user/quality-audit.yaml`
- `prompts/quality-audit-agent.md`
- `docs/processes/quality-audit.md`
- `examples/process-authoring/quality-audit/`
