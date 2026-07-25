# Release Checklist

Run these checks before publishing a ProcessForge release:

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
