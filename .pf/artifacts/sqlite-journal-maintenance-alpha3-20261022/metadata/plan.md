# Alpha3 publication metadata: bounded delivery plan

This primary sub-Work records the actual alpha3 release after the parent has
qualified and published it. It owns only the opt-in alpha feed, the alpha3
historical sidecar, and its own evidence/log/scratch. Primary owns the checksum
inventory separately; the source tag stays on the qualified source commit.

Current alpha feed contains alpha1; stable feed latest is 1.2.0. Preserve every
existing version object and the exact stable feed bytes. Do not invent an alpha2
history entry while publishing alpha3. Source commit is
`0bcf2a274a2097cf2ec84aa3a084644039390406`; publication is still pending.

Domain: an opt-in alpha distribution record identifies actual immutable ZIP bytes,
source commit/tag, provenance sidecar, compatibility and release notes. Its hash,
size, URLs and publication date must come from verified publication receipts.
The historical sidecar must equal the published native sidecar byte for byte.
No live installed configuration, update apply, context refresh or service action.

Implementation ordering:

1. Capture alpha/stable feed hashes and a private exact alpha baseline.
2. Wait for source/public/full archive-consumer gates and both-provider published
   release readback, including exact assets and source tag.
3. Insert one alpha3 version, set alpha latest, retain alpha1 unchanged, and copy
   the exact published sidecar to `release/1.3.0-alpha3/`.
4. Validate the normalized manifest through the existing native CLI. Exercise
   the existing UpdateVersionSelectionPolicy: alpha1 and alpha2 select alpha3;
   alpha3 and 1.3.0 stable select nothing newer; stable filtering excludes alpha3.
5. Primary refreshes checksums in a separate clean delivery candidate, preserving
   foreign dirty Main/resources/platform files. Commit only owned metadata and
   PF evidence; push the same delivery commit to both dev remotes and read back.
6. Verify the remote feed, exact sidecar and final tag/asset hashes. Close this
   sub-Work and parent with truthful delivery evidence; stop at this task boundary.

The existing normalized schema and version-selection owner are reused. This is
release data work, with no new production Python owner or product dependency.
Validation failures block metadata delivery; they never trigger automatic device
repair or stable-channel publication. Any retry preserves prior receipts.
