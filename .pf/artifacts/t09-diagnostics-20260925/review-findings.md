# T09 primary review

Independent bounded Python review: worker-code-review.md, followed by worker-review-followup.md (pass). Reviewer did not write core Python and did not perform PF transitions; prior docs/schema ownership is explicit. Primary inspected and fixed each concrete finding.

Resolved:
- Legacy hook debug initially bypassed project locks. It now passes through layered project/session/invocation policy; locked private sink cannot be changed to stderr, and invalid override turns optional collection off with a fixed non-sensitive notice. Regression exercises this failure path.
- Prompt/environment aliases initially escaped exact matching. Family matching and camel-name normalization omit documented sensitive aliases in all sinks/export.
- Idle export initially ignored retention. Export now applies effective cutoff to records and expired files, without deleting inputs; active-file retention also uses bounded first-record timestamp rather than only latest write time.

Primary additional checks/fixes: bounded traversal without full arbitrary-container copies; numeric request-id filtering; private paths with spaces; aggregate truncation labels; exact Work selection applies preferences without choosing a Work itself; setup failures remain optional; two-process writes share the lock and total log quota.

Mandatory event schemas/writers remain unchanged; common Host provider interpretation remains T04. Current journal, raw receipt and authorization checks are retained. Product source has no open blocking finding after these fixes and the final focused checks.

Validation qualification: one broad-batch isolated Runtime startup exited 1 after earlier standalone success. The test removed that initial fixture before diagnostics capture. Two subsequent isolated/final runs passed; the preserved stopped fixture was archived and checked before cleanup. Cause is not established; retain this test reliability observation for T06 instead of claiming it repaired or calling every historical attempt green. Initial public-cleanliness failure was a literal synthetic credential marker in the regression source; equivalent synthetic input is now assembled explicitly and validator passes.
