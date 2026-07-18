# Process Authoring Process Example

This example documents the built-in `process-authoring` process. Use it as the
reference flow when adding a new process pack:

```bash
python bin/pf.py process-authoring-start --project-root <project-root> --id <process-id> --title "<title>" --apply
python bin/pf.py process-authoring-review --project-root <project-root> --process <process-id>
python bin/pf.py process-authoring-apply --project-root <project-root> --process <process-id>
python bin/pf.py process-doctor --project-root <project-root> --process <process-id>
```

The generated process pack should include a process definition, agent prompt,
process documentation, and a portable example.
