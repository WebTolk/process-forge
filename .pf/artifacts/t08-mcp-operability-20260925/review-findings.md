# T08 — review findings

Result: PASS within T08 scope. Reviewer: primary agent; pinned single_agent process
forbids subagents, so this is a documented primary review, not an independent review.

Existing source fix c810381 is contained in a180ad6. The prior session delivered
the coherent manifest-owned package; this session verified the restarted host.
No source patch, freshness bypass, forged production session or host-config change.
All registered prior-stage artifacts and immutable main capsule retain their hashes.

Required live acceptance passed: same fresh snapshot/process/resources, positive
fixture search/resolve, negative authorization, sessionless Garage, real-host Work
lifecycle, rejected evidence recovery, and exact Work continuation in a new stdio
connection. Genuine stale manifest remains blocked. Six installed regressions pass.

## Residual observations outside the T08 repair

1. Main project has two legacy project-local resources; neither is in the physical
   Workplace catalogue. Main MCP search returns zero and global search readiness
   still says ready (85 documents). search-catalogue-diagnosis.json records the
   empty intersection. Do not claim project-local full-text coverage. Carry this
   distinction into T01/T02 resource/readiness contracts; no main snapshot mutation.
2. Existing php.class-doc-block template registry target is unresolved. The initial
   fixture probe honestly recorded zero results and unresolved navigation, then
   selected existing docs.api.gitverse:root through normal context refresh. Shared
   registry/config was not repaired or changed in this task.
3. Runtime remains ready/running with health degraded because another registered
   project lacks its PF manifest. Historical /event WinError10053 root cause is
   still uninvestigated. T08 does not qualify the whole Workplace as healthy.

These observations do not invalidate the demonstrated T08 transport/provenance,
authorization and governed-lifecycle behavior. They remain explicit follow-up
boundaries, not suppressed test failures. Public release qualification was not run.
