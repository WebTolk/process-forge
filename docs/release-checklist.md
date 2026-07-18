# Release Checklist

Run these checks before publishing a ProcessForge release:

```bash
python -m py_compile tools/processforge.py
python tools/validate-process-forge-schemas.py --root .
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-check --root .
python tools/smoke_first_run.py
python tools/smoke_resource_management.py
python tools/smoke_resource_authoring_processes.py
python bin/pf.py release-test --root .
python bin/pf.py release-pack --root . --output dist/processforge-release.zip
python bin/pf.py release-archive-test --archive dist/processforge-release.zip
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
