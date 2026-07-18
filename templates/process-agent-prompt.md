# <Process Name> Agent

Process id: `<process-id>`

Use the canonical Python launcher:

```bash
python bin/pf.py process-doctor --project-root <project-root> --process <process-id>
python bin/pf.py run-create --project-root <project-root> --id <run-id> --title "<title>" --process <process-id> --apply
```

Rules:

- Read the process definition before starting work.
- Record durable artifacts for every blocking gate.
- Run review before handoff when the process defines a review stage.
- Keep public files portable and free of secrets.
- Use run, task, iteration, review, and handoff files for traceable work.
