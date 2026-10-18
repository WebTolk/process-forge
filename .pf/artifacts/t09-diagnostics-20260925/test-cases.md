# T09 acceptance matrix

| Area | Positive / negative behavior | Evidence |
|---|---|---|
| Levels | 8x8 threshold matrix; convenience/log parity; unknown even off rejected | smoke_diagnostics |
| Profiles/config | Same CLI/MCP result; different detail; exact selected Work/session overrides; unknown version, limits and locked fields rejected safely | smoke_diagnostics |
| Expiry/sampling | Absolute expiry and record cap return to normal; debug lazy context not evaluated when disabled | smoke_diagnostics |
| Privacy | Synthetic credentials, sensitive aliases and exceptions removed in all sinks; hostile repr/cycles bounded | smoke_diagnostics; review follow-up |
| Required journal | All profile events/evidence persist; journal failure propagates under off; full process comparison separately | smoke_diagnostics; process invariance regression |
| Protocol | JSON-RPC validation/notification silence; real source stale error; hook success/failure neutral responses and locked legacy debug | focused MCP/hook tests |
| Correlation | Concurrent A/B sessions/Work isolated; sessionless null; real freshness reason and source build | smoke_diagnostics |
| Failure | ENOSPC/permission/serializer/lock/setup failure cannot replace result; serious loss notice bounded | smoke_diagnostics |
| Storage | 10000 writes with repeated rotation under 16 KiB test quota; age cutoff; two-process writer lock | smoke_diagnostics |
| Export | Request/run/time filter, numeric request ID, private paths with spaces, no overwrite/input changes; idle expired data excluded | smoke_diagnostics; sanitized bundle |
| Performance | Disabled 100000 <=0.5s; memory 10000 <=5s; JSONL 10000 <=20s | final-checks.json |
| Compatibility | Existing source Runtime/worker/Work/search cases and project-private policy preserved | assurance-results.json plus qualified final-checks.json |
| Public source | Schema, checksums, cleanliness, links and syntax | final-delivery-verification.json and validator results |
