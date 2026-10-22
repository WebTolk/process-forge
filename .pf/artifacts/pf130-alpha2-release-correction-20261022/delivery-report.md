# Corrected dev delivery

GO for 1.3.0-alpha2 dev archive and installed device build. Version correction
source commit is fe0f15072538fee9525792ae5b8c1e634b13a928. Its archive and sidecar
are committed separately with public verification evidence. Both dev remote refs
are read back after push; GitVerse uses token authentication.

The new native update is core-update-20261022T162745Z. This explicitly authorized
successor corrects the earlier alpha1 label and preserves that earlier history.
Source, archive, installed VERSION/manifest/CLI agree on alpha2. Installed hashes,
data preservation, shared usage/replay, workplace and new App Server checks pass.

Prior accounting implementation and unrelated facade/platform WIP remain intact.
No stable channel/tag update, new feature, repeated apply or speculative MCP host
restart is included. Existing connected hosts still need their own reconnect to
qualify loaded-module provenance.
