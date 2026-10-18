# Handoff: installed delivery -> original T06 actual-host acceptance

Objective: reconnect the application's ProcessForge MCP to the delivered Core and finish the original T06 acceptance gate with actual-host evidence.

Current governed state: delivery Run `garage-t06-delivery-prerequisite-qualify-a-clean-isolated-candidate-cont` completed through release-delivery and evolve (`action: run_completed`, 2026-09-26T11:52:56Z). The actual MCP then resumed the original T06 with `action: continue_existing`, exact original identities and the sole missing gate assurance-complete. Raw transitions and continuation response are stored in the delivery evidence directory.

Open closeout metadata finding: delivery run-doctor flags the absolute installation path copied into its original objective. See closeout-metadata-finding.md and closeout-verification.json. Do not describe delivery metadata validation as fully green or rewrite its immutable capsule to silence the check. Original T06 and installed payload checks are separate. Future objectives should use portable target labels, with machine paths confined to private operational evidence.

Final actual pf.context retry succeeded: snapshot fresh, original T06 current at code-assurance, sole missing gate assurance-complete. See final-actual-context.json. The earlier timeout is retained as an observation, not an ongoing transport outage. This still uses the pre-delivery loaded host tool surface; new-host acceptance remains pending.

## Delivered identity

- Source main remains `dev` at `a180ad624442d4fbe8ac1710073ef7d4c44babc4`, with reviewed uncommitted product work preserved. This delivery additionally corrected executable diagnostics examples in EN/RU and their checksum inventory.
- Detached candidate commit `69110c50559d994d7a31e751b7cd7afc989698db`; tree `39d3afd1f7d465e99f20c2b45cb875b398158b49`.
- Candidate checkout: `D:\dev\process-forge\.pf\tmp\t06-installed-delivery-20260926\candidate`.
- Archive: `D:\dev\process-forge\.pf\artifacts\t06-installed-delivery-20260926\delivery-package\processforge-1.1.0-t06-69110c50.zip`.
- Archive SHA256: `73b588243ec8bd8ffb9d73ab4dabaa323f62c55f26709ef149f3ef6dd5c4c42e`. Adjacent `.manifest.json` records clean source provenance. This is a local test-stand candidate, not a public release.
- Installed Core: `D:\.agents\processforge`. Workplace: `D:\.agents\processforge-workplace`. All 987 owned file hashes match the delivered manifest.
- Update: `core-update-20260926T085223Z`, status applied; 33 added, 37 changed, 0 removed, 917 unchanged, no local conflicts and no Workplace migration. Automatic Workplace doctor PASS.
- Backup: `D:\.agents\processforge\runtime\core-update\backups\core-update-20260926T085223Z`. All 37 backed-up file hashes and old/new control manifests verified.
- Runtime restarted with its original `--port 0 --interval 2.0`. New instance `d4fdb1b8c94547af84020213fcea087c`, pid 18160 at observation, endpoint `http://127.0.0.1:58278`, started `2026-09-26T08:52:28Z`. Runtime ready; doctor 7 PASS plus the unchanged unrelated degraded-health warning for missing plg-content-varreplace project config. Re-read identity; PID/port may change.

## Evidence and boundaries

Delivery evidence root: `.pf/artifacts/t06-installed-delivery-20260926/`. Read candidate-test-report.md, candidate-review.md, candidate-corrected.json, install-result.json, installed-verification.json, installed-stdio-proof.json and delivery-report.md. Append-only log: `.pf/logs/t06-installed-delivery-20260926.md`.

Candidate archive quick passes; 22 selected candidate checks have passing evidence (21 unchanged feature results plus corrected docs recheck). Installed diagnostics and seven further feature/transport smokes pass. 44 config/snapshot/capsule hashes, 561 prior frozen artifacts, and 986 current source payload files remain unchanged during install verification. Diagnostics performance is a bounded fixture measurement, not production latency proof.

Preserved observations: the extra post-install doctor command initially used the wrong flag; the correct `doctor-workplace --root` passed, as had the updater's automatic doctor. The source-wide checksum scanner reports ten actual-only Joomla user-process files outside both old and new Core manifests; unowned-inventory-proof.json records their hashes. Do not delete them or rewrite installed checksums. Initial stdio harness omitted required context_id and treated a business denial as a protocol error; corrected harness retains the initial observation separately. A current application's pf.context call timed out at its 60-second tool limit during post-install checks; do not represent it as new-host acceptance.

The application's MCP was started before delivery. Replacing disk files and starting a separate stdio process do not reload that connection. Its current tool surface still lacks pf.work.search and pf.work.resolve. Do not kill it by PID, fabricate a Ledger session or hot-patch its imports. Use a genuine client reconnect/new Codex session against the configured installed entry point; no further Core apply is required.

## Original T06 continuation

- Run: `garage-t06-pf-vision-alignment-r02-integrate-acceptance-for-work-resourc`.
- Assignment: `t06-pf-vision-alignment-r02-integrate-acceptance-for-work-resources-norm`.
- Stage: `code-assurance`; missing gate: `assurance-complete`.
- Expected capsule SHA256: `8bd7af0ba78c19c7c3aedb3e80d8d45436511ed0fa4090e501b1536dfa5467a6`.
- Snapshot: `ctx-20260925-140110-0dbc7c`, SHA256 `f73d8d332313f45a99d4e7b943e18bf4e812b44a51d4d8c682e8291b0753a562`, fresh without refresh.
- T06 capsule was created by the older installed Core and is legacy_contract_incomplete for new Work resource reads. Never overwrite it. Create a separate isolated current-contract fixture for the new-tool acceptance, attach its evidence to original T06 and resume original Work for completion.
- Earlier handoff: `.pf/handoffs/t06-integrated-acceptance-20260926.md`.

Resume using pf.work.start with the exact objective in the existing T06 assignment. Do not start a duplicate implementation Work. Check returned Run/Assignment ids and current stage before any transition.

Required actual-host checks after reconnect:

1. Discover pf.work.search and pf.work.resolve from the real connected tool surface; verify installed paths/hashes, fresh context, authorized project resolve and denial outside the selected snapshot. Preserve missing_session for a Forge-only view when no real Ledger session exists; do not invent identity. Existing project search has a known empty catalogue, so use an explicit fixture for positive search coverage.
2. Prepare a new isolated fixture under `.pf/tmp/` with the delivered installed constructor and a complete immutable Work contract, declared small resources and explicit run_id/assignment_id/context_id. Exercise positive Work search/resolve and negative unselected/revoked/drift/stage-subset access through the real connected MCP. Preserve evidence and context bytes; do not register unrelated projects globally.
3. Compare quiet/normal/diagnostic/trace/off with unchanged lifecycle/authorization semantics through the accepted host route. Existing installed isolated tests already prove source behavior but do not replace this layer. Confirm only canonical JSON-RPC on stdout, silent notifications, bounded diagnostic sinks.
4. Record actual connection continuity and exact Work/stage on reconnect; keep capsule bytes unchanged. The source/installed subprocess recovery fixtures already pass death/collection/invariance/transition checks.
5. Attach new evidence to original T06, satisfy assurance-complete only when actual-host checks pass, then finish release-delivery/evolve with honest references to this completed prerequisite. T07/T10/UI remain out of scope.

## Commands and recovery

Completed apply command (do not repeat):

```powershell
python -B D:\dev\process-forge\.pf\tmp\t06-installed-delivery-20260926\candidate\bin\pf.py core-update apply --core-root D:\.agents\processforge --archive D:\dev\process-forge\.pf\artifacts\t06-installed-delivery-20260926\delivery-package\processforge-1.1.0-t06-69110c50.zip --workplace-root D:\.agents\processforge-workplace --confirm
```

Read-only status commands:

```powershell
python -B D:\.agents\processforge\bin\pf.py core-update status --core-root D:\.agents\processforge
python -B D:\.agents\processforge\bin\pf.py runtime status --workplace D:\.agents\processforge-workplace --json
python -B D:\.agents\processforge\bin\pf.py runtime doctor --workplace D:\.agents\processforge-workplace
python -B D:\.agents\processforge\bin\pf.py doctor-workplace --root D:\.agents\processforge-workplace
python -B D:\.agents\processforge\bin\pf.py project-context-check --project-root D:\dev\process-forge --workplace D:\.agents\processforge-workplace --strict --json
```

Rollback is not currently needed or executed. If required, inspect the exact update backup/control plan and current hashes before a separately authorized rollback. Stop only the idle named Runtime, restore changed files from `files/` after matching old hashes, remove only added files still matching this candidate, restore the old manifest last, then restart with port 0/interval 2.0 and verify. Preserve unknown files, all Workplace configs, existing earlier T08 backup and all journals. A partial failure must be classified with read-only `core-update repair` before further action; never blindly repeat apply.

Pre-install evidence copies: `.pf/artifacts/t06-installed-delivery-20260926/pre-install/` (old manifest, previous last-apply, Runtime service metadata and logs). Current Runtime logs: `D:\.agents\processforge-workplace\runtime\pf-runtime\logs\`; updater result: `D:\.agents\processforge\runtime\core-update\last-apply.json`.

Files not to touch: existing pinned processes/capsules, frozen evidence, unrelated dirty source changes, user files outside Core ownership and other projects. Candidate and extracted scratch trees are declared retained evidence until actual-host T06 acceptance; after that remove the detached worktree with Git (without force) and only verified paths inside this delivery's `.pf/tmp/` directory. Preserve durable archives and proof files.
