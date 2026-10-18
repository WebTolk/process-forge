# Handoff: primary audit orchestrator -> remediation owner

Objective: Complete the interrupted Python/MCP/Runtime audit with actual junior
PF shell workers, independent verification and isolated remediation tasks.

Current status: Audit content accepted. Eleven independently reproduced defects,
four P1 and seven P2. Product fixes have not started. Declarative terminal proof
is recorded in the audit recovery directory.

Input artifacts:
- .pf/artifacts/codebase-audit-20260910/report.md
- .pf/artifacts/codebase-audit-20260910/remediation-tasks.yaml
- .pf/artifacts/codebase-audit-20260910/recovery-20260911/primary-findings.md
- .pf/artifacts/codebase-audit-20260910/recovery-20260911/acceptance.md
- .pf/artifacts/context-collection-20260910/acceptance-20260911.md

Files changed: Private PF assignments, launch capsules, reports, evidence,
runtime attempt records, logs and handoffs only. 651 baseline product files
are unchanged at commit 901d0551773fe7a5b382b89ebe95b212b0747e83.

Files not to touch: Historical audit originals, archived attempt1/attempt2
records, immutable capsules, unrelated runs/dirty projections, installed Core,
Workplace resources and update backups.

Known issues: MCP start reports stale while source context is fresh because
classifier display-path representation changes across distribution roots (A09).
Collection rejects absolute-path text in authenticated reports (A06); expected
report containment is separately broken (A02). Other verified issues cover
search file-root containment, update journal failure, scheduler liveness/health,
session identity, JSON-RPC validation, singleton orphan handling and lifecycle
event identity. Hook delivery mock H01 was not accepted as a defect.

Required checks: Reproduce each assigned defect before repair; minimal change;
negative controls; independent junior review after implementation; primary
acceptance. Serialize writers for tools/processforge.py, host.py and service.py.
No release qualification inferred from audit evidence PASS.

Next recommended action: Separate governed remediation, operationally A09 first
to unblock MCP bootstrap. Then prioritize A01/A02/A03/A10. A02 precedes A06.
Existing diagnosis is sufficient to design bounded fixes; do not blindly refresh
the snapshot or restart MCP as a substitute for correcting the classification
contract. Installation/publication remains separately authorized delivery work.
