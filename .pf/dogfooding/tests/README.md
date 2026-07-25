# ProcessForge Dogfooding Tests

This directory contains project-local stabilization and regression smokes for ProcessForge itself.
They are not part of the public release archive and are not included in `release-test --public`.

Run commands:

```bash
python .pf/dogfooding/run_dogfooding_tests.py --list
python .pf/dogfooding/run_dogfooding_tests.py --suite supervisor-stress
python .pf/dogfooding/run_dogfooding_tests.py --suite dev-contract --fail-fast
python bin/pf.py dev-test --root . --suite supervisor-stress
```

The runner sets `PF_REPO_ROOT` before launching each script, so scripts can stay under `.pf/dogfooding` while still exercising the repository-local CLI and templates.
