# Installed Core delivery result

PASS for the separately governed installed test-stand delivery prerequisite. Original T06 actual-host acceptance remains incomplete. No public release, main-branch commit/push, project migration or unrelated infrastructure repair.

Final candidate `69110c50559d994d7a31e751b7cd7afc989698db`, tree `39d3afd1f7d465e99f20c2b45cb875b398158b49`; archive `delivery-package/processforge-1.1.0-t06-69110c50.zip`, SHA256 `73b588243ec8bd8ffb9d73ab4dabaa323f62c55f26709ef149f3ef6dd5c4c42e`. Candidate/archive assurance is in candidate-test-report.md and candidate-corrected.json.

## Installation

Manifest-controlled update to `D:\.agents\processforge` completed at `2026-09-26T08:52:23Z`, update id `core-update-20260926T085223Z`. The repeated pre-apply plan matched 33 added, 37 changed, 917 unchanged; no removals, local conflicts or missing owned files. Workplace migration not applicable. Existing Runtime was idle, stopped gracefully and restarted using original port 0/interval 2.0. No host MCP process was killed/restarted by PID.

All 987 installed payload hashes/sizes match the final manifest. All 37 backup file hashes and control old/new manifests match. Backup directory: `D:\.agents\processforge\runtime\core-update\backups\core-update-20260926T085223Z`. No incomplete journal; last-apply is applied. Automatic and explicit Workplace doctor passed. Runtime ready; doctor 7 PASS with the same pre-existing unrelated degraded-health warning. Original fresh project snapshot/capsule and shared configs were preserved without a refresh workaround.

Raw evidence: install-result.json, installed-verification.json, pre-install/ and the installed update backup/control/plan.json. The install script's extra doctor invocation used an incorrect flag after successful apply/start; correct `doctor-workplace --root` passed in follow-up. The failed invocation remains visible; apply was not repeated.

## Installed validation

Eight installed smokes PASS: diagnostics; prepared execution crash/recovery; Work resource binding; complete context parity; diagnostic profile/process invariance; MCP JSON-RPC validation; provider adapter admission; supplemental Runtime/Ledger/hooks/MCP integration. All registered checks used their normal timeouts. Diagnostics ran without concurrent smoke load: disabled 100,000 calls median 0.155752 s, memory 10,000 records 0.842022 s, JSONL 10,000 writes 12.784798 s, bounded storage 16,384 bytes. These fixture numbers do not characterize actual-host latency.

Post-test integrity: 987 installed owned hashes; 44 protected config/snapshot/capsule hashes; 561 earlier frozen evidence hashes; 986 current source payload hashes all verified unchanged. The source-wide checksum scanner also sees ten pre-existing unowned Joomla process files and reports them as actual-only. All ten paths are absent from both old/new ownership manifests (unowned-inventory-proof.json); do not remove user files to make a source-only inventory scan green. Owned integrity is verified by the installation manifest. This observation is preserved in installed-inventory-observation.json.

Two separate installed stdio connections PASS: new pf.work.search/pf.work.resolve discovery, fresh project context, exact current delivery Work/stage, authorized project resolution, out-of-snapshot denial and missing_session without fabricated identity. JSON-RPC-only stdout, silent notifications, empty stderr and EOF 0. Original T06 CLI retains its exact Run/Assignment at code-assurance; its legacy immutable capsule is correctly denied for new Work resource reads with legacy_contract_incomplete. Raw evidence: installed-stdio-proof.json. The initial harness schema mistake is retained in stdio-harness-schema-observation.json; corrected calls include required context_id and evaluate business denial as documented.

The actual application's older MCP still has its pre-delivery tool surface. One pf.context call timed out at 60 seconds during checks; a later actual pf.work.state succeeded and returned this delivery Work at release-delivery. Neither observation is acceptance of a newly loaded host build. Actual client reconnect and fixture/profile checks remain on original T06.

Release-readiness decision: ready and delivered to the local installed test stand. Delivery profile: executed (clean candidate, release-pack, extracted archive quick, 22 selected candidate checks, serial manifest apply, rollback/integrity/config checks, eight installed tests, separate stdio reconnect). UI/browser profile not applicable: no UI change. Public release/full release-suite qualification not claimed.

Continuation and exact paths/commands/rollback boundaries: `.pf/handoffs/t06-installed-delivery-reconnect-20260926.md`. Candidate and extracted scratch trees are retained as declared delivery evidence until actual-host T06 acceptance.
