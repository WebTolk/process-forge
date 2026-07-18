# Content Update Process Authoring Example

This example shows a content workflow with intake, draft, editorial review, and
handoff stages.

```bash
python bin/pf.py process-create --project-root <project-root> --answers examples/process-authoring/content-update/answers.yaml --apply
python bin/pf.py process-doctor --project-root <project-root> --process content-update
```
