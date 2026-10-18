# T08 — test matrix history

Current result after restart: **PASS for T08**. Live host checks, fresh connection
continuation and genuine stale guard passed. Main Work reached run_completed.
Authoritative final matrix: test-cases.md; verdict and limits: test-report.md.
The interim matrix below is preserved as the historical pre-restart checkpoint.

Status: partial; live host validation pending session restart. Do not register this as
assurance-complete. Source / archive / installed / connected host are separate evidence layers.

| Case | Layer | Actual result |
|---|---|---|
| Stable classification provenance across distributions; genuine change detectable | source + installed regression | PASS |
| JSON-RPC envelope, invalid args, notification silence | source + installed regression | PASS |
| Actionable missing-session diagnostics | source + installed regression | PASS |
| Authorized SQLite search; path traversal denied; cross-project session rejected | source + installed stdio fixture | PASS |
| Manifest ownership, missing files, migration source validation | clean source 3 regressions | PASS |
| Package/source/sidecar hashes and safe entries | archive | PASS |
| Fresh extracted CLI + quick tests | archive extracted | PASS |
| Every installed owned file equals manifest | installed 954 files | PASS |
| Same snapshot fresh after delivery, no refresh | installed CLI | PASS |
| Existing Workplace doctor | installed | PASS |
| Runtime start/readiness, auth/lock/protocol | installed | PASS with health WARN |
| Main project context fresh via current host MCP | live host | PENDING restart |
| Authorized search/resolve and denied resource | live host | PENDING |
| Isolated Work start/state/transition/completion | live host | PENDING |
| New MCP connection resumes exact fixture Work | live host / reconnect | PENDING |

## Review findings

No new source patch; existing regression-tested classifier fix was absent from installed Core.
Manifest-controlled coherent delivery chosen over manual one-file hotpatch. No local conflicts,
no removals, no Workplace migration. Runtime WARN is named external project missing its PF
manifest; outside T08 scope. Overall health must not be presented as entirely green.

## Next tests

After restart check context first. If still false stale compare live process entry point and bytes,
not VERSION alone. Use advertised MCP schema and PF state to select authorized resource ids.
Use a uniquely named isolated fixture under .pf/tmp, preserving main T08 Work and old assignments.
Do not relax freshness or fabricate a Ledger identity; security negatives need controlled fixture.
Keep exact request/response outcomes in a new live-acceptance artifact; only then freeze final
review/test report and satisfy assurance gate.
