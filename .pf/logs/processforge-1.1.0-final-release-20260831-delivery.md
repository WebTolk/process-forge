# Release delivery log: ProcessForge 1.1.0

## 2026-08-31T05:04:33Z — release-manager / codex-main

- Scope: exact-tag source qualification and deterministic packaging.
- Files: clean worktree at `07b1fb68011f5928be824f0c7343322992cf809a`,
  `dist/processforge-1.1.0.*`.
- Status: source 186/186 PASS; ZIP built with 910 entries.
- Follow-up: extracted archive and installed-upgrade proof.

## 2026-08-31T05:23:56Z — release-manager / codex-main

- Scope: official public 1.0.2 -> final ZIP upgrade.
- Files: isolated temporary installation and updater journals only.
- Status: plan/apply/status/checksum/release-check PASS.
- Risk: hosted Codex MCP remains an external host-session check.

## 2026-08-31T05:57:46Z — release-manager / codex-main

- Scope: extracted archive qualification.
- Files: persistent extracted final ZIP, release-test JSON/Markdown/trace.
- Status: full fail-fast rerun PASS with one expected non-Git WARN.
- Risk: the first wrapper run had one non-reproduced failure whose detailed
  output was discarded by its temporary-directory wrapper.

## 2026-08-31T05:59:54Z — release-manager / codex-main

- Scope: remote Git/tag/GitHub Release publication.
- Files: tag `v1.1.0`, two GitHub Release assets, `release/**`, final `.pf`
  delivery artifacts.
- Status: old remote tag deleted; final tag and public GitHub Release live;
  asset digest/size verified.
- Follow-up: open a fresh MCP-enabled Codex host session for the explicitly
  documented external acceptance item.
