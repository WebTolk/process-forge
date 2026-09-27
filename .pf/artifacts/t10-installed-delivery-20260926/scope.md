# Scope and acceptance

Deliver the accepted first terminal monitor slice to installed Core through release-pack, release-archive-test, core-update plan/apply/status. Retain backup and command evidence. This is local installation, not public publication.

Acceptance: isolated clean candidate based on the previously delivered commit; exact normalized parity with current public source; delta restricted to the nine reviewed T10 paths; archive and extracted checks pass; updater no conflicts/migration surprises; installed manifest and all owned hashes match archive; preexisting unknown files/configuration remain unchanged; installed monitor and relevant regressions pass; Runtime liveness/readiness restored if restarted. A loaded host MCP may remain the prior process; distinguish its proof from new subprocess/package proof.

Out of this delivery Work: implementing metrics/tray/egress, repairing active event journal, changing unrelated project registry, publishing a release, rewriting frozen evidence. These are not hidden as completed. Known old NDJSON finding is preserved and isolated from public package validation. The user requested remaining work too; investigate and continue it after installed delivery.
