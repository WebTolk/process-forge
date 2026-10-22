# Correct release identity to alpha2

2026-10-22. Operator states alpha1 has already been released and this delivery is
alpha2. The prior dev package was incorrectly labelled alpha1 by the primary.
Preserve that archive, its approved reports and device-update receipt as history;
publish a new corrected artifact and one successor native update, not a replay.

Fresh PF context and exact new Work/capsule inspected. PF Python, practices and
packaging resources resolved; read the prerelease ordering guidance, PEP20,
Core/OOP placement rules, Python QA context and shared Python toolchain contract.
No change to domain behavior or existing Core-property planning is introduced.

Scope: VERSION and common/release_identity.py move from 1.3.0-alpha1 to
1.3.0-alpha2; regenerate shipped checksums in a clean committed candidate. The
legacy facade's separate 1.2.0 constant is outside this correction and unchanged.
Existing accounting behavior, archive layout and project/spec versions remain.
The new archive is processforge-1.3.0-alpha2-dev-20261022.zip with its sidecar.

Use a new sparse clean candidate with all three required public .pf projections.
Registered Ruff lint/format and scoped mypy cover the changed typed module;
existing release/version and updater checks plus native archive qualification
verify identity end to end. Existing same-byte accounting QA remains applicable.
No mirror tests or broad repository audit are needed for two version values.

Before one native apply, inspect plan, preserve mutable config/common SQLite and
backup it. Gracefully stop the intended App Server, install, verify all managed
hashes, version/manifest consistency, shared usage/replay, workplace doctor and
new Runtime health. Existing MCP-host reload remains a separate host action.

Commit scoped changes/artifacts, push identical dev heads to both remotes using
token auth for GitVerse, complete native stages and stop. No stable channel/tag
change or unrelated refactor is included in this correction.
