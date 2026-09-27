# Prepared delivery candidate

Status: ready_for_review. No installed files changed yet.

Detached candidate commit 7ecfac349c5494b9a902f3a7e28d8c5e03341bf1, tree 5817a99bd2b0d2934007b5506cbfb708e321653e. Main branch remains a180ad624442d4fbe8ac1710073ef7d4c44babc4 with its pre-existing uncommitted work. All 986 current product source paths match the candidate after release newline normalization; main source hashes are unchanged. Candidate delta is 70 files (the reviewed T01-T06/T09 implementation/docs/tests and manifest/checksums), with clean Git provenance.

Archive: delivery-package/processforge-1.1.0-t06-7ecfac34.zip.
SHA256: ec36643ec0fd3ee08f3caf077da01be023b136bdad0a9d158421dac2d63fbd00.
release-pack PASS. release-archive-test source/archive/sidecar parity and extracted quick PASS (126.725 s), including schema/public/checksum/bootstrap/ingress/conversation/replay checks. Archive contains 988 entries and 987 Core-owned payload files. This is a test-stand delivery candidate; full public release suite is not claimed.

Read-only installed plan: 33 added, 37 changed, 0 removed, 917 unchanged, 0 locally modified, 0 missing owned, no blockers. Workplace migration not_applicable. Installed prior payload is 954 files. Runtime ready/running, active_workers=0, pending_runtime_jobs=0. Existing degraded health belongs to the unrelated plg-content-varreplace registration; no repair is in scope. Runtime and install checks will be repeated immediately before apply.

Build harness initially hit WinError 206 on a long git-add argv; changed it to an exact NUL-delimited pathspec file and verified the same base/parity before resuming. Evidence preserved. No product code or main-index mutation resulted.

Additional feature/update/doc checks run from independently extracted verified payload, followed by semantic plan review. Only after assurance will release-delivery stop the verified idle target Runtime, apply the manifest update, verify backups and restart it with prior settings. Current host MCP remains untouched until a genuine client reconnect.
