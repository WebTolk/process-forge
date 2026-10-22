# Alpha publication metadata: verified existing contracts

The current opt-in alpha feed uses the normalized `subjects[].versions[]` shape,
contains only alpha1, and points at the published alpha1 archive. The stable feed
latest is 1.2.0. Exact original feed hashes are in [baseline.json](baseline.json).

The applicable contract is `schemas/normalized-update-manifest.schema.json`,
not the legacy `processforge-update-index` shape. It requires a generated time,
subject identities, version/channel/stability/prerelease/yanked/source fields
and artifact URL/hash. Existing artifact fields also support byte size and a
provenance URL. Existing alpha1 entry can remain unchanged while alpha3 is added.

Native validation already exists as `update manifest validate --file`. The
existing `UpdateVersionSelectionPolicy` in
`src/processforge_core/maintenance/versions.py` normalizes normalized manifests
by requested channel, retains actual archive URL/hash/size, and compares existing
prerelease precedence. It performs no fetching, installation or update apply.
Use that exact owner for focused selection assertions; add no production logic.

Only the opt-in alpha feed, a new versioned sidecar and parent-owned checksum
inventory are affected. Stable metadata, source tag, package contents and existing
history remain immutable. The source tag predates publication metadata to avoid
a circular archive hash. A later delivery metadata commit records the actual
qualified package and final lifecycle evidence on both dev remotes.

Both-provider published readback remains a blocking prerequisite to writing the
new version object. All URLs, sizes, hashes and publication times will be taken
from those actual receipts. Full archive/consumer qualification is a parent gate.
