# Core Boundary Scan Guards Handoff

Implemented in this slice:

- `tools/processforge.py`
- `tools/core_boundary_smoke_helpers.py`
- New `tools/smoke_*` boundary and trace checks
- Boundary, snapshot, installation, doctor, and limitation docs
- `.pf/process-forge.yaml` explicit `processforge-development` project type

Verification completed:

- Full public release-test with and without fail-fast passed with
  `--trace-smokes`.
- `dist/processforge.zip` rebuilt with 692 files.
- Full extracted archive test passed.
- Schema, public cleanliness, checksum, and `git diff --check` gates passed.

Known follow-up:

- Consider a public `project-source-inventory` CLI only after the helper proves
  stable in doctors and smokes.
