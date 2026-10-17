# Operator plan: SQLite dev release and device cutover

User explicitly requested: make a dev release, update installed PF, migrate the journals to SQLite, then restart app-server. This authorizes the required installed Core and writer lifecycle operations. The source-only result and earlier restart are insufficient.

Exact Work: `garage-hook-sqlite-device-cutover-20261017-user-authorized-dev-release-a` / `hook-sqlite-device-cutover-20261017-user-authorized-dev-release-and-devi` / `hook-sqlite-device-cutover-20261017-user-authorized-dev-release-and-devi-capsule`; capsule checksum `sha256:3374b1095c803bca8335e3dc96337211c716022965719d545541aaa3d9b96309`. Context `ctx-20261016-091113-310bed` is fresh, policy continue, exact capsule valid/ready, no overlap or blockers. No platform/toolchain overlay selected. No subagents permitted. This is an artifact-only operator Work; source implementation is already delivered.

Plan and sequencing:

1. Inspect existing pack/update/migration and managed writer controls; inventory actual project journals and source damage.
2. Build an immutable dev archive from `69c59ec7e86d0a1e8aaf2cc8c4e59491969448ab` in isolated scratch; verify archive contents, focused source evidence and short extracted launch.
3. Prepare native update plan, backups and reviewed migration preflight before changing the device.
4. Quiesce old Runtime/MCP/hook writers, preserve journals, perform one native Core apply and migrate selected actual project journals with stable source hashes. Retain originals and any damaged rows as explicit evidence.
5. Start the updated Runtime, verify SQLite writes/retry and legacy stability, measure CPU against the retained 20.7354% settled baseline. Verify actual connected MCP separately; do not claim a standalone process is the connected host.
6. Record exact archive/install/migration/process evidence, complete Work, commit owned records and publish the same SHA to both dev remotes using token authentication for GitVerse.

General PF 1.2.0 acceptance and stable publication remain outside this task. Preserve unrelated dirty files, immutable capsules and earlier evidence. Failures require readback, never blind repeated apply or live-lock deletion.
