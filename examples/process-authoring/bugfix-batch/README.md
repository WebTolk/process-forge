# Bugfix Batch Process Authoring Example

This example shows a multi-task process where each bug can be tracked as a task
with work, debug, fix, review, and handoff iterations.

```bash
python bin/pf.py process-create --project-root <project-root> --answers examples/process-authoring/bugfix-batch/answers.yaml --apply
python bin/pf.py process-doctor --project-root <project-root> --process bugfix-batch
```
