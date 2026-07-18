# SEO Audit Process Authoring Example

Create the example process from prepared answers:

```bash
python bin/pf.py process-create --project-root <project-root> --answers examples/process-authoring/seo-audit/answers.yaml --apply
python bin/pf.py process-doctor --project-root <project-root> --process seo-audit
```

Expected public outputs:

- `processes/seo-audit.yaml`
- `prompts/seo-audit-agent.md`
- `docs/processes/seo-audit.md`
- `examples/process-authoring/seo-audit/`
