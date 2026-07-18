# Create Your First Process

Start with guided authoring:

```bash
python bin/pf.py process-authoring-start --project-root ../my-project --id seo-audit --title "SEO Audit" --apply
python bin/pf.py process-authoring-review --project-root ../my-project --process seo-audit
python bin/pf.py process-authoring-apply --project-root ../my-project --process seo-audit
python bin/pf.py process-doctor --project-root ../my-project --process seo-audit
```

The authoring session is private project flow state under
`.pf/authoring/processes/seo-audit/`. The applied process pack is public project
content under `processes/`, `prompts/`, `docs/processes/`, and
`examples/process-authoring/`.

To create from prepared answers:

```bash
python bin/pf.py process-create --project-root ../my-project --answers templates/process-authoring-answers.yaml --apply
```

Then use the process in a run:

```bash
python bin/pf.py run-create --project-root ../my-project --id seo-audit-run --title "SEO audit run" --process seo-audit --apply
python bin/pf.py task-create --project-root ../my-project --run seo-audit-run --id task-001-audit --title "Audit homepage" --process seo-audit --apply
python bin/pf.py iteration-add --project-root ../my-project --task task-001-audit --kind work --summary "Initial audit completed." --apply
python bin/pf.py iteration-add --project-root ../my-project --task task-001-audit --kind debug --summary "Checked missing evidence." --apply
python bin/pf.py task-complete --project-root ../my-project --task task-001-audit --summary "Audit task completed." --apply
python bin/pf.py run-summary --project-root ../my-project --run seo-audit-run --apply
python bin/pf.py run-doctor --project-root ../my-project --run seo-audit-run
```
