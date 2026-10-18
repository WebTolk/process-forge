# Delivery architecture and implementation plan

Status: ready_for_review. No product service change planned.

1. Snapshot source product hashes and private evidence pins; create detached worktree from current HEAD. Overlay reviewed checksum-owned product bytes only, verify exact normalized parity, create local candidate commit, and require clean Git provenance. Do not commit main source.
2. Run candidate release/source gates plus new feature, documentation, initialization, update and context tests relevant to this combined delivery. Use ordinary timeouts and preserve failures. Build a durable archive/sidecar and run archive parity plus extracted quick; run delivered feature tests from extracted/installed bytes as appropriate. Do not claim full public-suite qualification.
3. Obtain exact read-only installed update plan, old manifest/config hashes, runtime status/doctor/log backups. Abort apply on conflicts, missing owned files, non-idle workers/jobs or unexplained migration. Do not force.
4. Stop only the verified existing target Runtime gracefully. Apply from independent candidate with --confirm. Verify manifest payload hashes, every changed-file backup and serial Workplace migration result. Preserve all journals. Restore the Runtime with prior settings and verify context/doctor/installed tests.
5. Record final archive/candidate/backup/build identities and a restart-ready handoff. Complete this bounded delivery Work only after its checks pass. Resume the original T06 acceptance Work; actual connected-host checks remain pending until client reconnect exposes the installed tools.

Recovery: on failure inspect core-update status/repair without retrying blindly. Before manifest publication, restore exact changed/removed bytes from backup, remove only newly added paths whose hashes match this transaction and write the old manifest last. After published manifest/partial Workplace migration, follow the recorded manual-repair plan; never infer a safe global rollback. Preserve T08 backups as well.
