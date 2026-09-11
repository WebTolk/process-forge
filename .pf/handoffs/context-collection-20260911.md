# Handoff: diagnostic orchestrator -> bounded remediation

Objective: Finish existing context-origin and worker report-capture diagnosis.
Current status: Primary diagnosis accepted; both shell tasks are done and their
shell run is completed. Declarative terminal proof is stored alongside artifacts.

Input artifacts:
- .pf/artifacts/context-collection-20260910/primary-recheck-20260911.md
- .pf/artifacts/context-collection-20260910/acceptance-20260911.md
- .pf/artifacts/context-collection-20260910/report-capture/report.md
- .pf/artifacts/codebase-audit-20260910/remediation-tasks.yaml

Files changed: Diagnostic brief, corrected junior report, primary evidence and
acceptance, PF task/capsule/run records, logs and handoff. No product changes.
Files not to touch: Preserved attempt1 evidence, unrelated active/historical runs,
approved reports/capsules, installed Core and Workplace.

Known issues: A09 classifier display paths cause source/MCP freshness mismatch.
A06 automatic content filtering rejects legitimate authenticated report text.
A02 expected report containment is missing. Duplicate raw receipt alone does
not prevent retry derivation; that former explanation was rejected.

Required checks: Fix semantic classifier parity without hiding true changes;
enforce canonical report containment before reading; then accept authenticated
path-like report text while preserving secret/provenance/hash/exact-one guards.
Use disjoint junior assignments and primary independent regression verification.

Next recommended action: Separate remediation scope for A09, then A02/A06.
Do not refresh the context or restart infrastructure as a substitute for the
known source defect. This handoff does not authorize installed apply or release.
