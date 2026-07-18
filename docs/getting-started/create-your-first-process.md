# Create Your First Process

Start with guided authoring:

```bash
cd ../my-project
python .pf/runtime/bin/pf.py process-authoring-start --project-root . --id seo-audit --title "SEO Audit" --scope project --kind operational --apply
python .pf/runtime/bin/pf.py process-authoring-review --project-root . --id seo-audit
python .pf/runtime/bin/pf.py process-authoring-apply --project-root . --id seo-audit --apply
python .pf/runtime/bin/pf.py process-doctor --project-root . --process seo-audit
```

The authoring session is private project flow state under
`.pf/authoring/processes/seo-audit/`. The applied process pack is public project
content under `processes/`, `prompts/`, `docs/processes/`, and
`examples/process-authoring/`.

To create from prepared answers:

```bash
python .pf/runtime/bin/pf.py process-create --project-root . --answers templates/process-authoring-answers.yaml --apply
```

Then use the process in a run:

```bash
python .pf/runtime/bin/pf.py run-create --project-root . --id seo-audit-run --title "SEO audit run" --process seo-audit --apply
python .pf/runtime/bin/pf.py task-create --project-root . --run seo-audit-run --id task-001-audit --title "Audit homepage" --process seo-audit --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task task-001-audit --kind work --summary "Initial audit completed." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task task-001-audit --kind debug --summary "Checked missing evidence." --apply
python .pf/runtime/bin/pf.py task-complete --project-root . --task task-001-audit --summary "Audit task completed." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run seo-audit-run --apply
python .pf/runtime/bin/pf.py run-doctor --project-root . --run seo-audit-run
```
