# Process Authoring MVP Handoff

Status: implemented locally.

Key files:

- `tools/processforge.py`
- `tools/smoke_process_authoring.py`
- `processes/process-authoring.yaml`
- `prompts/process-authoring-agent.md`
- `docs/authoring/process-authoring.md`
- `docs/getting-started/create-your-first-process.md`
- `examples/process-authoring/`

Verification completed:

- `python bin/pf.py release-test --root .` -> pass
- `python bin/pf.py release-archive-test --archive dist/processforge-v0.1.0.zip` -> pass

Commit status: local changes are ready for review; no commit was requested in this task.
