# T01 — domain model and rules

Work is the project/run/assignment tuple, independent of transport, provider and
session. An execution attempt is a retry of one Work and one context revision.
Snapshot generation identifies project selection at context creation; a context
revision is a separate immutable contract for one Work. Stage projection derives
current inputs/outputs/gates/subset from the pinned process and stage state.

Resource identity is its selected id plus version/generation and a verifiable
fingerprint of the declared material. Metadata search pins metadata, not an
undeclared recursive content copy. Unversioned content is usable only when a bounded
manifest can verify the required material; otherwise return an explicit unavailable
or unverifiable diagnostic. Mutable Work outputs remain journal/evidence resources,
not frozen input corpora that invalidate themselves on every stage artifact write.

Effective access = pinned Work grants intersect current authorized project grants
intersect stage subset intersect available capability/path constraints. Any explicit
deny wins. A stage may narrow access, never add it. Omitted subset means inherit
Work grants; explicit empty subset means no resource grants. Revocation blocks new
access even if old data remains on disk. A new current grant cannot enter old Work.

Scope separates read, write and forbidden paths/actions. Empty allowlist grants
nothing. Required outputs are obligations, not implicit permission to write an
arbitrary path. Internal PF state writes belong to the process service, not to an
unbounded worker grant. Analysis-only denies product writes. Required capability
missing blocks prepare before executor launch; optional missing is a named warning.

Public context uses portable ids/path_refs; private resolved paths live in runtime
preparation only. A declarative grant governs PF interfaces and launcher preparation;
it is not a claim that arbitrary executor OS access is sandboxed by a prompt.

Adapter identity is trusted registration, not ingress payload authority. Adapters
normalize provider events and attest their specific provenance; common Host verifies
registered identity, project/session/attempt/evidence binding and raw-first handling.
Unknown adapter is quarantined/denied; no dynamic import path supplied by an event.

Process journal records mandatory durable facts. Diagnostics describe operations
and may be filtered/off. Severity is seriousness; profile is volume/detail; threshold
filters severity; sink is an output; correlation ties request/Work/attempt/snapshot.
Sessionless means session absent/null, never a fabricated session. Disabled diagnostics
cannot suppress explicit result errors or required evidence/journal failures.

Examples and negative/legacy diagnostics will be fixed in the architecture matrix
and public contract. No implementation claim is made by this domain artifact.
