# Domain and rules

Source identity: exact clean Git commit/tree. Release tag must later point to that exact commit. Canonical archive contains the distributable payload and generated Core manifest. Sidecar remains outside the ZIP and hashes its final bytes. A rebuild with different bytes invalidates previous hashes.

Publication identity: immutable GitHub assets and historical sidecar are distinct from the mutable stable channel. Channel promotion occurs after published asset/hash verification, not while preparing an unpublished candidate. Metadata committed later avoids source-commit self-reference.

Installed acceptance: previous dev payload/device/runtime/actual host proof is separately retained. Archive parity can demonstrate unchanged payload but cannot invent a stable publication, a new real worker or cross-platform acceptance. Installing Core requires explicit confirmation; journal migration and host lifecycle are separate operator operations.

Boundaries: project schema/startup-contract/process/release versions stay independent; current source remains unchanged. Unknown/partial metrics and platform limits stay explicit. Stage inputs/capsules immutable. New artifacts own one scope. Future publication needs explicit maintainer approval per current product release notes.

Handoff: source->archive->metadata checks in owned scratch, with exact byte identities and qualified publication plan.
