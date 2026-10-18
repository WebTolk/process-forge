# Create Your First Process

Use an onboarded project and the Python environment from
[installation](installation.md). Start an authoring session, then edit its
`answers.yaml` to describe stages, artifacts and gates before review/apply:

```bash
cd ../my-project
python .pf/runtime/bin/pf.py process-authoring-start --project-root . --id quality-audit --title "Quality Audit" --scope project --kind operational --apply
```

Fill in `.pf/authoring/processes/quality-audit/answers.yaml`, then review the
proposal and apply the agreed definition:

```bash
python .pf/runtime/bin/pf.py process-authoring-review --project-root . --process quality-audit
python .pf/runtime/bin/pf.py process-authoring-apply --project-root . --process quality-audit --apply
python .pf/runtime/bin/pf.py process-doctor --project-root . --process quality-audit
```

The authoring session is private project flow state under
`.pf/authoring/processes/quality-audit/`. The applied process pack is public project
content under `processes/`, `prompts/`, `docs/processes/`, and
`examples/process-authoring/`.

To create from prepared answers, adapt the distribution’s
`templates/process-authoring-answers.yaml` into a project-local answers file
(for example under `.pf/tmp/process-authoring/`) and pass its actual path.
The template is not automatically copied into a linked project:

```bash
python .pf/runtime/bin/pf.py process-create --project-root . --answers <answers-file> --apply
```

For ordinary execution, use the governed Work entry described in
[declarative process execution](../concepts/declarative-process-execution.md).
The following explicit run/task sequence is a compatibility example:

```bash
python .pf/runtime/bin/pf.py run-create --project-root . --id quality-audit-run --title "Quality audit run" --process quality-audit --apply
python .pf/runtime/bin/pf.py task-create --project-root . --run quality-audit-run --id task-001-audit --title "Audit input" --process quality-audit --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task task-001-audit --kind work --summary "Initial audit completed." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task task-001-audit --kind debug --summary "Checked missing evidence." --apply
python .pf/runtime/bin/pf.py task-complete --project-root . --task task-001-audit --summary "Audit task completed." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run quality-audit-run --apply
python .pf/runtime/bin/pf.py run-doctor --project-root . --run quality-audit-run
```
