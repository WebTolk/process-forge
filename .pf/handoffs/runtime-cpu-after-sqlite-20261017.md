# Handoff: current Runtime profile -> bounded scheduler/Host design

Objective: remove the remaining measured Runtime CPU cost without replaying the successful SQLite dev cutover. Read .pf/artifacts/runtime-cpu-after-sqlite-20261017/report.md for quantified actual stacks and the concrete owner boundary.

Current state: updated Runtime9716 ready/degraded, installed source69c59ec, native apply core-update-20261017T064646Z complete, four project-local SQLite databases ready; legacy333files unchanged. CPU18.587%/60s. Current30s GIL profile1980samples/0errors: scheduler86.92%, ingress12.12%, metrics0.81%. Main buckets: Run discovery49.55%, all Host JSON I/O30.61% (inclusive of parent owners). Active discovery parses569run.yaml/16MB before filtering terminal runs; Host state37.8MB is fully read/written on repeated ticks and ingress.

Concrete new scope candidates: Runtime scheduler orchestration in service.py, Host load/save/registry/deferred-capture owner in host.py, and the bounded Runtime caller of active_run_ids/command_supervisor_tick. Keep generic public Work/CLI authoritative reads and current lifecycle/gates semantics intact. Design invalidation/concurrency/durability before code. Do not delete old Work or deferred conversation bodies; do not invent a blind TTL cache or simply raise polling intervals as a claimed algorithmic fix.

No repair or infrastructure operation in the diagnostic Work. All source files remained unchanged. Any implementation needs a newly scoped exact Work; this read-only capsule and terminal predecessor cannot be broadened/reused. The current user instruction explicitly requested dev release/update/journal migration/restart, which is complete; the new profile identifies additional owners for the next repair rather than silently expanding that storage migration.

Actual connected MCP remains quiesced/Transport closed; fresh installed CLI fallback is the control plane. Do not restart/update again merely to refresh host tools. User host reconnection is needed for actual connected-MCP acceptance. General1.2.0 verification remains deferred.

Retain current diagnostic sampler hashes/raw folds/summaries and predecessor archive/backups. Preserve unrelated dirty state and immutable capsules. Publish own diagnostic evidence commit to origin/dev and gitverse/dev with full-SHA readback; GitVerse token only, no browser.
