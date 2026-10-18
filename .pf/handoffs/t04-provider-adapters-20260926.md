# Handoff: T04 -> T05

Objective: trusted provider adapters and neutral Host admission.
Current status: actual MCP run_completed, assignment done; run-doctor 21 PASS on 2026-09-26. Source qualification accepted, installed Core remains T08.
Input artifacts: .pf/artifacts/t04-provider-adapters-20260926/, particularly test-report.md, review-findings.md, final-checks.json, optional-init-proof.json, assurance-results.json and evidence/07-09.json.
Files changed: provider policies/registry, Host/replay, optional integration helper/Core/CLI wiring, narrow legacy batch membership repair, docs and registered tests. Exact hashes in final-checks.json; raw kernel and main capsule unchanged.
Files not to touch: frozen artifacts/capsules and unrelated dirty work; installed/shared infrastructure outside T06 delivery scope.
Known issues: symlink creation unavailable; source tests are not actual-host new-feature proof. Normalized Runtime remains its existing authenticated compatibility path. Inbound event data never registers code.
Required checks: 13 compatibility smokes, new alternate-provider regression, four actual optional-init scenarios, schema/public/checksum PASS; independent source review resolved. No full-release/package claim.
Next recommended action: automatically start T05 to prepare bounded authorized one-Work/attempt input and deterministic offline generic-shell proof, then T06 integrated/actual-host acceptance. No T07/T10/UI scope.
