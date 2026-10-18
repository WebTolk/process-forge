# Proposed publication metadata

These are the complete final file bytes proposed for the post-publication metadata commit, not the currently active stable channel. Apply only after the exact v1.2.0 assets are publicly verified and the publication Work has appropriate scope.

The sibling publication-metadata.patch.gz contains an unchanged unified diff against f975d3a7f54100c310bf3dced0f0bbbc256a7738. Its uncompressed SHA and gzip SHA are in promotion-materials.json. Raw patch is also retained in the owned scratch. Gzip preserves meaningful blank-context whitespace while allowing the evidence commit to pass ordinary git diff --check.

The archive/source commit stays f975d3a; these five follow-up files are deliberately committed afterward. The two existing QA expectations move to 1.2.0 and exactly two checksum entries change. Full readable content is under this directory, so reviewing the proposal does not require inspecting the compressed diff. The local update index and its checksum are already coherent with 1.2.0 in that source commit.

The historical sidecar copy is JSON-equivalent to the shipped native sidecar. Git may normalize text line endings; the actual upload file and its exact SHA remain identified separately in archive-identity.json.
