# Public Core Audit Report

## Findings

- `release-test --public` previously ran internal stabilization smokes for resource/update authoring, multi-agent orchestration, supervisor final drain, heartbeat regressions, and full shell-agent stress. That made the public release gate sensitive to local dogfooding timing.
- The release archive previously included a product checksum inventory from `.pf/artifacts/`, which conflicted with the required archive boundary.
- Schema and cleanliness validators treated internal smokes as required public files.
- The release checklist mixed public release gates and internal dogfooding commands in one flat command list.

## Changes

- Public release-test now filters commands by `public_gate=true`.
- Release-test reports each command with `layer` and `public_gate`.
- Internal smokes moved to `.pf/dogfooding/tests/scripts/`.
- `.pf/dogfooding/run_dogfooding_tests.py` runs dogfooding suites manually.
- `python bin/pf.py dev-test --root .` and `python bin/pf.py dogfood-test --root .` delegate to the dogfooding runner.
- Public checksum inventory path is now `checksums/processforge.sha256`.
- Archive checks reject `.pf/runtime/`, `.pf/artifacts/`, `.pf/reviews/`, `.pf/handoffs/`, `.pf/runs/`, `.pf/contexts/`, `.pf/assignments/`, and `.pf/dogfooding/`.

## Boundary

Public release tests prove the installable product surface. Dogfooding tests prove ProcessForge's own stabilization lab and are intentionally local-only.
