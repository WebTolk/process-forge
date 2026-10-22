# Code quality of the cumulative alpha3 release candidate r4

The registered Ruff lint/format, strict mypy and Bandit checks passed on the exact
[r4 candidate](source-candidate-r4.json); commands/exits/log hashes are indexed in
[QA receipts r3](qa-receipts-r3.json). Toolchain versions remain those in the prior
quality reports. No product dependency, global default, container or Main callback
was added. The maintenance owners/adapters and previous fixes remain unchanged.

The existing frozen ArtifactAuthoringService now accepts an explicit concrete
Path or deferred root callable, matching the evidence validator's existing pattern.
Pathless/justification-only and unsupported-format branches do not access a root.
Actual text containment still precedes opening the file; link checks bind their
actual root once. EvidenceValidationService injects the method without evaluating
it. Material validation's clock/path/containment/relative/hash order is retained;
the later advisory root read is explicitly asserted by the existing smoke.

The extensionless FakePath in that smoke now exposes its actual empty suffix.
No assertion was removed. Seven separate pytest cases exercise rootless evidence,
cold creation, real file/hash review, callback order and outside-root refusal
before file opening. All 530 final repository cases and the ten original smoke
cases passed, with the documented seven environment skips.

Only Git tracking of four prior dev distributions will be removed. Their original
local bytes remain guarded; prior commits/releases remain intact. Canonical Git
LF manifests and preserved local CRLF files have separate recorded hashes.
Independent review and aggregate public/archive/publication gates remain pending.
