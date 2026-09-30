# Release Checklist

Run these checks before publishing a ProcessForge release:

Prepare a clean source candidate with explicit root `AGENTS.md` and hidden
`.pf/AGENTS.md` projections containing the current versioned startup contract.
The canonical source is `templates/agent-entry-contract.md` and its metadata;
`templates/project-agents-template.md` is the verified extended projection.
Review any entry migration before applying it to an existing project. Candidate
preparation and project migration are separate from packing: `release-pack`
does not generate instructions or substitute a hidden file for a missing root.
The release gate rejects missing, stale, changed or inconsistent contracts.
Regenerate the candidate's checksum inventory after preparing its final layout.

```bash
python -m py_compile tools/processforge.py
python tools/validate-process-forge-schemas.py --root .
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-check --root .
python tools/smoke_first_run.py
python tools/smoke_runtime_driver_registry.py
python tools/smoke_worker_run_shell.py
python tools/smoke_process_supervisor_tick.py
python tools/smoke_director_inspector_boundary.py
python tools/smoke_agent_ledger.py
python tools/smoke_single_agent_session_flow.py
python tools/smoke_multi_project_agent_sessions.py
python tools/smoke_multi_agent_as_composed_sessions.py
python tools/smoke_project_coordination_modes.py
python tools/smoke_mixed_workplace_projects.py
python tools/smoke_worker_awareness_of_director.py
python tools/smoke_error_workflow.py
python tools/smoke_process_run_task_batch.py
python bin/pf.py release-test --root . --public --fail-fast
python bin/pf.py dev-test --root . --suite supervisor-stress
python bin/pf.py release-pack --root . --output dist/processforge.zip
python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full
git diff --check
```

Release output must not include:

- `.pf/runtime/`
- `.pf/artifacts/`
- `.pf/reviews/`
- `.pf/handoffs/`
- `.pf/runs/`
- `.pf/contexts/`
- `.pf/assignments/`
- `.pf/dogfooding/`
- `runtime/`
- `__pycache__/`
- temporary smoke directories
- private absolute paths
- local user secrets
- hook outbox payloads
- local transcripts
- stale `dist/processforge-v*.zip` archives or matching stale manifests
