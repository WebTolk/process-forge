# Human documentation release audit

Status: ready_for_review

## Blocking findings

- `QUICKSTART.md` and `QUICKSTART.ru.md` lack a prominent one-time workstation
  setup and still teach manual session/run mechanics as the ordinary scenario.
- No compact Garage/Forge lifecycle comparison is presented in the main
  getting-started path.
- Update defaults still use production-facing `example.com` URLs.
- The public migration file is named `1.1.0-prerelease-hardening.md` although
  the intended release is stable `1.1.0`.
- Maintainer publication order and exact-tag deterministic rebuild are not
  documented as one contract.

## Already aligned

`garage-core.md`, `runtime-mcp.md`, `runtime-autostart.md`, and hooks docs already
contain most of the correct lifecycle model. They need wording reconciliation,
not architectural replacement.

## Required documentation result

- one-time MCP registration for Codex;
- optional/required-on-Forge Windows Runtime autostart;
- everyday flow is simply opening Codex in the project;
- Garage/Forge table near the getting-started path;
- honest Linux autostart, hosted-MCP, optional-hook, and no-TUF limitations;
- stable `1.1.0` naming throughout release and migration documentation.
