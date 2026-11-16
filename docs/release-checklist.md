# Release Checklist

[Русская версия](ru/release-checklist.md)

Run these checks before publishing a ProcessForge release:

Prepare a clean source candidate containing the repository's root `AGENTS.md`,
`CONTRIBUTING.md` and `CONTRIBUTING.ru.md`. These are contributor instructions.
The source repository's root `.pf/` is private local state: a fresh clone and
distribution checks must work without it, and it must not enter the public
inventory or release ZIP. A local `.pf/AGENTS.md` is not a required release input
or a substitute for the root contributor policy.

The consumer startup contract is shipped separately as
`templates/agent-entry-contract.md` with `templates/agent-entry-contract.json`
metadata; `templates/project-agents-template.md` is its verified extended
projection. Release checks validate these templates and their integrity without
requiring contributor and consumer instructions to be identical. Review an entry
migration before applying it to an existing consumer project. `release-pack`
does not initialize the source project, generate instructions or rewrite the
root contributor policy.

Record the candidate's exact source commit/tree, included changes and applicable
verification results. After preparing its final shipped layout, regenerate the
inventory with `python tools/validate-process-forge-checksums.py --root . --write`,
inspect the complete inventory diff and run the checker again. A later source
change requires affected checks on the new identity. A source prerelease version
does not establish that a release has been published on a provider.

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
python bin/pf.py release-pack --root . --output .pf/tmp/release-check/processforge.zip
python bin/pf.py release-archive-test --archive .pf/tmp/release-check/processforge.zip --root . --extracted-test full
git diff --check
```

Release output must not include:

- the source repository's entire root `.pf/` directory
- `runtime/`
- `__pycache__/`
- temporary smoke directories
- private absolute paths
- local user secrets
- hook outbox payloads
- local transcripts
- stale `dist/processforge-v*.zip` archives or matching stale manifests

Use a writer-owned directory under `.pf/tmp/` for repository scratch. Record
the actual source commit, version and final archive SHA-256 in qualification
evidence. A later rebuild needs its own hash and applicable checks. See
[release publishing](maintainers/release-publishing.md) for publication and
mirrored-asset verification.
