# Handoff: dev-release -> actual MCP reconnect acceptance

Objective: закончить предрелизную приёмку установленного dev8ea152b после переподключения фактического PF MCP хоста.
Current status: Core установлен один раз; app-server перезапущен и ready; полный финальный consumer suite, 13 installed checks, HTTP/SQLite/новый независимый MCP PASS. Actual connected MCP остаётся прежним процессом; новый код в нём не принят. Work остаётся release-delivery, не terminal.
Input artifacts: .pf/artifacts/pf120-dev-release-20261017/report.md, public-summary.json, resume-checkpoint.json, archive-identity-final.json, installed-integrity.json, checkpoint-after.json, installed-mcp.json, connected-mcp-provenance.json, quiet-runtime.json.
Exact run: garage-pf120-dev-release-20261017-package-committed-work-metadata-projec
Exact assignment: pf120-dev-release-20261017-package-committed-work-metadata-projection-qu
Exact context: pf120-dev-release-20261017-package-committed-work-metadata-projection-qu-capsule
Capsule checksum: sha256:9b9b49dd8a156c764ef7517f8f96b5b3f164ae9ce3216cc94c3489c0beff46df
Native continuation: pf120-dev-mcp-reconnect-20261017 (create/readback receipt retained separately).
Qualified source: 8ea152bfa6376a66fc87c7ed48d74eacc5c2ad41
Applied ZIP SHA256: e332a74de958b2daad9711644bd848a82d1024b83bd03c47537377a27884a7dc
Files changed: own release evidence/handoff; supporting existing-test/checksum change delivered separately as8ea152b. Product projection delivered as280e00d. Private device data and immutable capsules preserved.
Files not to touch: prior capsules/approved inputs, unrelated dirty state, global raw_hooks=false/events=true, historical records, installed Core or server for repeated update/restart. Old ZIP999667c5 is superseded and never installed.
Known issues: actual MCP owner process predates apply; independent stdio proves the new code but not host reconnection. Default shutdown guard reaches a history budget; complete native idle proof preceded the explicit graceful override. Metrics partial values remain unknown.
Required checks: after actual host reconnect, call fresh pf.context, native continuation status/resume by this exact id, then exact Work state and authorized docs.python:root resolve. Verify actual process/root/start is new relative to the completed apply, source manifest/metadata hash matches checkpoint, and record actual warm pf.context (one warm-up +five). Do not refresh an already-fresh context merely because raw checkout CRLF disagrees with installed resources.
Next recommended action: finish only the remaining actual MCP gate, update own report/evidence, run native release/evolve transitions through run_completed, doctors, scoped commit and parallel push/full readback of both dev remotes. If actual MCP is still old, retain this Work and exact continuation; do not create a duplicate or claim loaded-code acceptance.
