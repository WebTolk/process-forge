# R01 result

Status: accepted source correction.

Changed files:

- `tools/smoke_user_like_garage_path.py`: asserts the documented first-run
  empty-corpus state, verifies project-context profile resolution, and preserves
  the no-infrastructure work-start assertion.
- `docs/concepts/garage-core.md`: distinguishes resolvable project-local
  resources from documents in the shared Workplace corpus.
- `checksums/processforge.sha256`: refreshed for the changed public files.

No production search, Garage, package registry, or authorization code changed.
The prior expectation contradicted the deliberate shared-index design. The
regression now protects against treating `empty` as an error or requiring a
project-local profile to be copied into a shared Workplace index.

The worker cancellation is retained as execution evidence. Primary validation
and review passed; no blocking task remains.
