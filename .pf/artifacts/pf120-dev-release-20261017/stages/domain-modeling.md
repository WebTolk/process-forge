# domain-modeling

Status: ready; primary / release-engineer, 2026-10-17.

Terms/rules: source commit identifies product; dev archive has immutable SHA and release/Core manifests; installed Core owns only manifest-declared files; workplace/project history and config remain separate. pf-app-server hosts Runtime scheduling, while CLI and MCP are separate adapters with independent module lifetimes. Fresh context does not prove new loaded bytes. Only a new verified candidate is applied once after full qualification and checkpoint. Guarded lifecycle verifies exact idle owner; no force bypass. Full suite uses isolated fixtures for mutating hooks, chat, Ledger, workers, Work and update tests. Actual device acceptance uses safe reads and bounded operational checks. Missing metrics remain unknown. These rules preserve existing contracts and device logging.raw_hooks=false/logging.events=true.

Next: follow the pinned native process and ../plan.md; do not edit this evidence after transition.
