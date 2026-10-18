# T08 — changed files / implementation summary

2026-09-25T14:32:22Z: installed Core updated successfully by manifest-based updater.
Target D:\.agents\processforge. Source commit a180ad624442d4fbe8ac1710073ef7d4c44babc4,
clean tree 0b0ff44185d1ef4bc62e18a7f12678be4f160efc, version remains 1.1.0.

## Changed files

Exact set is core-update-plan.json / core-update-apply.json: 27 owned files replaced,
12 added, 0 removed, 915 unchanged. No forced local modifications or missing owned files.
Core manifest now lists 954 payload files. Every installed payload hash independently
checked against manifest: 954 checked, 0 mismatches. core-update status installed,
incomplete_update=false. No new product source patch was required or made.
Unknown installed files and project/Workplace configs were not overlaid.
Workplace migration not_applicable; automatic doctor-workplace status pass.

## Before / after

Installed context-check now fresh=true, stale=false, broken=false, execution ready,
resource fresh, policy continue for SAME ctx-20260925-140110-0dbc7c and SAME snapshot
sha256:f73d8d332313f45a99d4e7b943e18bf4e812b44a51d4d8c682e8291b0753a562.
No context refresh was performed to obtain this result. Health warn remains distinct
from freshness. Durable result: installed-context-after.json.

Released tools/processforge.py SHA256 d3c100062981a351706c09f0808138edb6fe2ae7050a67a73fdbc306cb9a90be;
released tools/pf_runtime/mcp_server.py SHA256 404a7e00eb0d06097c616870ea03bd28200cf09d9c9f2a50ed3c5c8da4489bc1.
The primary checkout raw processforge.py hash 107786ac... differs only by CRLF;
normalizing CRLF to LF gives exactly released d3c100... . Clean candidate and installed
raw hashes match; no unexplained source delta. See hash-normalization.json.

## Runtime / preservation

Before update verified exact installed Runtime PID14088, active_workers=0, pending_jobs=0;
graceful runtime stop succeeded. Backup of old service metadata and all 3 runtime logs:
.pf/tmp/t08-core-package-20260925/runtime-before/.
Operator.log 3112328 bytes, runtime.stderr.log 3667430, runtime.stdout.log 0.
Existing live logs remain in Workplace and append; no logs truncated.

Update id core-update-20260925T143222Z. Backups of all 27 replaced files plus old/new
manifest and plan: D:\.agents\processforge\runtime\core-update\backups\core-update-20260925T143222Z.
No files deleted. No rollback performed; exact recovery guidance in architecture.md.

Runtime restarted from installed Core with same port=0 / interval=2.0, new PID2732,
started_at 2026-09-25T14:32:50Z, endpoint http://127.0.0.1:51324.
Runtime status ready, auth/protocol/lock/handle/Ledger doctor checks PASS, health degraded WARN.
Identified scheduler error is a pre-existing registered external project
D:\Dev\plg-content-varreplace missing .pf/process-forge.yaml; new scheduler diagnostics
expose it. Current process-forge project continues inspector tick; other project unchanged.
Do not initialize/delete/unregister that external project in T08. One operator-log request.error
WinError10053 at 14:33:56Z also observed; retain as diagnostic, not asserted root cause.

## Tests / boundary

Source 7 targeted tests PASS and archive extracted quick PASS already recorded.
Installed separate-process tests all exit 0: smoke_classifier_distribution_parity.py,
smoke_mcp_jsonrpc_validation.py, smoke_mcp_missing_session_diagnostics.py,
smoke_project_init_local_search_mcp.py. The last test launches real installed stdio server
with isolated Workplace/projects and checks allowed search, traversal denial and session mismatch.

Host-owned MCP remains the old loaded process until operator restarts the session.
Implementation delivered; T08 acceptance NOT complete. Do not mark assurance-complete
or run_completed until live-host acceptance and continuation checks recorded.
