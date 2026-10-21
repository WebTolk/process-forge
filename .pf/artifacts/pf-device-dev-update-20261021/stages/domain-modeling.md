# Operator domain and invariants

The source commit identifies accepted code; the private archive and its ownership
manifest identify the byte payload. Installed Core status/manifest identify disk
state. Workplace is independent persistent device data with only archive-declared
migrations. Runtime is a long-lived loaded process; its PID/readiness and loaded
provenance require post-update evidence. Monitor is a read-only console client.
The connected host MCP is a separate loaded process and is not reconnected by
replacing Core files or restarting Runtime.

Apply once after a read-only plan; use the manifest-controlled updater and native
backup/journal. Preserve unknown/unowned files, existing configuration and project
contexts. Do not reinitialize Workplace, rewrite capsules or start unrelated
indexing. A normal Runtime restart must respect active/unknown activity; observe
the guard rather than treating old passive Work records as fresh execution proof.
Health, readiness and statistics coverage remain independent results.

Handoff: no product design is needed. The implementation plan is the explicit
operator sequence with private targets, exact source/manifest and recovery proof.
