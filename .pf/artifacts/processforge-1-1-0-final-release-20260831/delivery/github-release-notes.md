ProcessForge 1.1.0 is the stable release following 1.0.2. Versions 1.2.0 and
1.2.1 were internal update-mechanism fixtures and are not public releases.

Highlights:

- sessionless Garage flow through `pf.context`, `pf.search`, `pf.resolve`, and
  `pf.work.start`;
- host-owned stdio MCP lifecycle without a Runtime daemon requirement for
  Garage;
- long-lived Forge Runtime and opt-in Windows Task Scheduler autostart;
- managed Core updates, stable-channel discovery, deterministic release
  provenance, and archive-sidecar verification;
- generic project onboarding no longer requires or installs Codex hooks;
  host hooks remain optional telemetry.

Upgrade from 1.0.2:

The public 1.0.2 package predates the managed Core updater. Extract the 1.1.0
ZIP to a temporary staging directory, back up the installed Core, and run the
1.1.0 `core-update plan` and `core-update apply --confirm` commands against the
installed Core path. See `docs/getting-started/update-system.md` for the exact
procedure.

Release assets:

- `processforge-1.1.0.zip` — deterministic distribution archive;
- `processforge-1.1.0.manifest.json` — archive checksum, source commit/tree,
  full file inventory, and official-pack provenance.

SHA-256 (`processforge-1.1.0.zip`):
`81c3c6708efc3c2a68882d16e716dc49749734c81d44f598767fdbd36a32d8be`
