# Implemented alpha3 public-gate prerequisite

`ArtifactAuthoringService` now receives a concrete Path or a deferred explicit
root provider. Its frozen construction, pathless evidence, justification-only
review and unsupported file formats do not invoke that provider. Filesystem
containment is checked before opening actual text, and link checks use one bound
root for that operation. Existing concrete-Path consumers retain their behavior.

`EvidenceValidationService` passes its existing root method without calling it.
The material clock/path/containment/relative-path/hash order is preserved. The
existing smoke now explicitly asserts the later advisory text-review root read;
its extensionless-path fake exposes the actual empty suffix. All ten original
cases pass. Seven new pytest cases prove pathless behavior, cold construction,
actual content/hash review and refusal before opening a file outside the root.
The focused authoring/evidence pytest run passed all 111 cases.

The cumulative [candidate r4](../primary/source-candidate-r4.json) retains all
maintenance implementation bytes from CODE GO r3 and adds four scoped source/test
paths. It excludes only four tracked previous dev distributions. Exact original
local hashes and sizes are in [prior-distributions.json](prior-distributions.json);
the original files are preserved on disk. Candidate copies were verified against
their exact Git blobs before removal; JSON LF versus local CRLF was distinguished.
Git untracking will be committed only after final independent review.

Registered cumulative candidate lint, strict typing and Bandit have passed;
the complete candidate pytest run and fresh independent review are pending at
this implementation handoff. The failed first public gate and all previous
candidate/review/QA evidence are retained. Parent owns final checksums and release.
