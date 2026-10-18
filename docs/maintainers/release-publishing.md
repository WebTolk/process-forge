# Release Publishing

This is the maintainer contract for a public ProcessForge release.

1. Prepare a clean release source candidate and finish product documentation.
2. Run source schema, cleanliness, checksum, and full release tests.
3. Create and push the final source commit.
4. Create `vX.Y.Z` on that exact source commit and push the tag.
5. Build the archive from a clean checkout of that exact tag/commit.
6. Generate the release sidecar next to the archive; never include the sidecar
   inside the ZIP whose bytes it hashes.
7. Repeat archive hash/parity and full extracted-archive tests.
8. Publish the ZIP and sidecar as immutable GitHub Release assets.
9. Commit the historical sidecar copy under `release/<version>/` and update the
   mutable `release/updates/processforge-stable.json` channel document.
10. Verify an installed previous release discovers the stable version and that
    installation still requires explicit confirmation.

The historical sidecar records the tagged source commit/tree. Release metadata
generated from that commit is committed afterward, avoiding a commit-hash
self-reference. If a rebuild changes ZIP bytes, the rebuilt SHA-256 is
authoritative and every public metadata reference must be updated before
publication. Do not preserve an obsolete candidate hash.

For a release mirrored across hosts, publish identical ZIP/sidecar bytes and
the same tagged source commit on each required host. Verify remote asset hashes
and update discovery after publication. Authorization to publish and successful
publication are separate facts: do not label a candidate as published before
the maintainer confirms the actual release.

Reusable command examples can use neutral archive names. Qualification evidence
must preserve the actual release version, tagged source commit and SHA-256 of
the bytes checked. Keep repository scratch in `.pf/tmp/`; retain durable
evidence before removing owned intermediates.

ProcessForge uses HTTPS, SHA-256, immutable assets, and Git provenance.
TUF-backed trust metadata is future hardening, not a current capability.
