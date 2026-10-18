# T02 Work resource binding regression

**Result:** PASS on the final run (`python -B tools/smoke_work_resource_binding.py`, exit 0; about 2 minutes). The exercise uses temporary Workplace/project roots and source MCP/CLI processes; it does not touch the main project state.

The regression checks CLI/MCP parity, Work A pinning across a later A+B authorization, B isolation from A, a second authorized session continuing A, and denial of a session bound to another project. It verifies provenance survives a real prepare-to-build transition and checks the pinned capsule bytes remain unchanged through reads, refresh, and negative cases. It also covers metadata body mutation, fulltext mutation/deletion, declared version change, current-access revocation, explicit empty stage subset, expanded invalid subset, missing/unsupported binding, checksum tampering, exact/missing selectors, path traversal, fresh global index versus partial authorized coverage, and document-byte budget enforcement for metadata/fulltext in both content-capture modes.

The budget check confirms `include_content=False` and `True` produce identical bindings for the same fulltext material. Symlink rejection could not be exercised: this Windows host rejects symlink creation, reported as `unsupported by host` by the script.

Harness corrections during validation:

- The continuation comparison now ignores the expected `stage_id` difference, asserts current stage `build`, and compares all remaining result/provenance fields. First run failed only because it compared the pre-transition `prepare` payload byte-for-byte.
- Fixture B now uses a distinct resource ID (`manual`). A prior attempt reused `guide`; the fixture helper deduplicated that logical ID, so the intended A+B authorization was not created.
- Synthetic subset fingerprinting imports `canonical_fingerprint` from `processforge_core.process_execution`; a prior attempt incorrectly looked for it on the CLI module.
- One run reached test cleanup after its assertions but failed with Windows `PermissionError` removing the temporary shared SQLite index. This exposed a real connection-close gap in `authorized_coverage` (and a similar in-memory search connection). Primary fixed both with explicit closure. After that product fix and removing the test GC workaround, the final full regression exited 0.

No other product defect surfaced in this run. The symlink branch remains unverified on this host; the bounded regression and assertions are in `tools/smoke_work_resource_binding.py`.
