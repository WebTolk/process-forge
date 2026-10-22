# Bounded prerequisite repair for the alpha3 public gates

The first committed-source public run failed at the existing evidence validation
smoke (two errors and one ordering assertion), before packaging. It also rejected
four tracked distributions from previous development deliveries. Failed receipts
remain under the first source qualification attempt; no alpha3 tag or release
has been created. Maintenance candidate r3 remains unchanged and CODE GO.

Verified cause: `EvidenceValidationService.normalize` constructs the advisory
authoring service with an eager `_root()` before processing even pathless evidence.
The older validation contract deliberately keeps root providers deferred and
permits pathless/rootless early returns. The authoring service only needs a root
for actual filesystem review, so eagerly resolving it violates that boundary.
Both affected owners are unchanged by the maintenance feature commit.

Scope: primary owns `evidence/validation.py`, `evidence/authoring.py`, the existing
evidence validation smoke, `tests/evidence_authoring/test_lazy_root.py`, the exact
four stale development distributions and this Work's artifacts/log/scratch.
Parent owns the checksum inventory and final candidate. No maintenance behavior,
CLI/MCP payload, process/capsule, paused OOP work or device service is changed.

Domain and architecture: advisory authoring consumes explicit existing evidence
and a deferred root dependency. Construction and pathless/justification-only
review must not resolve the project root. Existing validation still performs its
clock/path/containment/relative-path/hash callbacks in order. Actual text-file
authoring follows material validation and may then resolve its explicit root.
Keep the frozen dataclass and narrow callable injection already used by evidence
validation; add no global context, container, Main callback or hidden default root.

Implementation: let ArtifactAuthoringService accept the existing concrete Path
or an explicit `Callable[[], Path]`, resolving it only in filesystem branches.
Pass the existing root method as a callable from validation. For link checking,
bind one actual root inside that operation. Existing concrete-Path callers retain
their behavior. Update the old trace assertion to distinguish completed material
validation from the subsequent advisory root read; do not remove an assertion.
Add independent cases proving no root access for pathless declarations and N/A,
real-file callback order/content findings, outside-root refusal and cold creation.

Distribution hygiene: record hashes and sizes of the four tracked previous dev
ZIP/sidecars. Remove only their Git tracking in the fix commit; preserve exact
original working-tree files. Delete only the matching invocation-owned copies
inside the private clean candidate, after checking resolved containment and bytes.
Historical Git commits and previous published releases remain available.

Validation: run the existing focused evidence/authoring smokes and applicable
pytest, registered lint/format/strict typing/security, then the whole repository
suite. Freeze a new cumulative manifest without altering r1/r2/r3 or old reviews.
The same independent reviewer must inspect the fresh candidate in a separate
read-only Work. Only after CODE GO commit/push the repair, rerun complete public
source and full archive/consumer gates, and publish alpha3. Any failure remains
blocking and is retained. No unverified publication or live update is performed.
