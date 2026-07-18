# Release Checklist

Run these checks before publishing a ProcessForge release:

```bash
python -m py_compile tools/processforge.py
python tools/validate-process-forge-schemas.py --root .
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python tools/processforge.py release-check --root .
python tools/smoke_first_run.py
python tools/smoke_resource_management.py
python tools/smoke_resource_authoring_processes.py
python tools/processforge.py release-test --root .
python tools/processforge.py release-pack --root . --output dist/processforge-v0.1.0.zip
python tools/processforge.py release-archive-test --archive dist/processforge-v0.1.0.zip
git diff --check
```

Release output must not include:

- `.pf/runtime/`
- `runtime/`
- `__pycache__/`
- temporary smoke directories
- private absolute paths
- local user secrets
- hook outbox payloads
- local transcripts
