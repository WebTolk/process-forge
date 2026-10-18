# Delivery investigation, impact and domain

Status: ready_for_review. Source T06 has nineteen passing distinct smokes, clean syntax/schema/public/checksum/link gates and frozen context/evidence hashes. Earlier T01-T05/T09 handoffs qualify local source but defer installed host acceptance. T08 established a successful manifest-controlled test-stand update and rollback journal pattern. Its physical installation still exposes neither new Work read tools nor work_context/diagnostics modules.

Current release-pack checks source cleanliness, public content and checksums, emits deterministic normalized files plus a Core manifest and sidecar provenance. release-archive-test checks source/archive parity and an extracted quick/full subset. This is a bounded test-stand candidate, not a new public release qualification; do not equate selected tests with the complete release-test suite.

Core ownership manifest, not a whole-directory copy, controls add/replace/remove. Changed owned bytes conflicting with the old manifest block apply. Unknown files and runtime/project/workplace state are outside payload ownership. Core update applies serially before any declared compatible Workplace migration. Backup/control manifests and journal are the rollback authority; no blind repair/rollback after a partial migration.

Candidate creation must preserve the main dirty tree, include new untracked product modules/tests listed in the current checksum inventory, and exclude private artifacts/ZIPs. Main source and installed VERSION remain 1.1.0; commit/tree/module hashes identify the actual build. Reviewable delta and exact plan precede installation. Runtime idle status is separate from unrelated degraded scheduler health. Existing sessions and capsule pins must never be regenerated to hide drift.
