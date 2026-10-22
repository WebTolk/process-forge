# Native checksum surface and release metadata

The clean metadata candidate was recalculated and validated through the existing
native checksum tool. Its inventory remains byte-identical: SHA256
`5112a0d7c201224f2a4e73bdd45732a98e44efdf17d0181c7f6e30fffb3ee5e1`.
There are no `release/` entries in that native checksum surface. This is the
existing contract; do not broaden the surface or manufacture an inventory change.

Release-data assurance instead binds the actual published archive/sidecar hashes,
native normalized schema, existing version selection, exact Git blob bytes and
both remote refs. The metadata commit therefore owns three changed files: alpha
feed, exact historical sidecar and its version-local byte-preservation attributes.
Parent's clean Main and all published source/package bytes remain unchanged.
