# Beta release qualification — orchestration plan

## Goal

Produce, install, and qualify a ProcessForge beta on this machine using a
clean release checkout, isolated workplace/project fixtures, and durable
evidence. A beta is GO only after archive, installation, functional, security,
MCP/Codex, and regression gates pass.

## Sequence

1. Preserve local evidence, synchronize a clean beta baseline with `origin/dev`,
   record environment and candidate commit/tag.
2. Build a deterministic archive; validate manifest, hashes, public surface,
   and full extracted suite.
3. Install the archive into a new isolated distribution/workplace/project
   layout; verify launcher and doctors.
4. Run initialization/repair, search/resolve, process-obligation, MCP stdio,
   real Codex, security, recovery, and Windows cleanup scenarios.
5. Run full regression from the installed beta; collect evidence and issue GO/
   NO-GO with product defects separated from environment blockers.

## Required gates

- clean candidate and deterministic archive provenance;
- full `release-test --public --fail-fast` and full extracted archive test;
- clean installation and repeated installation without duplicate state;
- initialization `complete`, repair safety, fresh snapshot, doctor PASS;
- snapshot-bound FTS states, pagination, provenance, no cross-project/workplace fallback;
- MCP stdio contracts and a real Codex session with `pf.session_context` then `pf.search`;
- path/session/write security boundaries;
- worker/event/conversation/replay regressions and Windows cleanup lifecycle;
- durable beta validation report with archive SHA-256 and exact installation paths.

## Current constraints

- The active checkout has post-commit report artifacts and is behind the latest
  remote checksum-inventory commit; beta packaging must use a fresh clone.
- A real Codex MCP call may be blocked by approval policy `never`; record that
  as an environment blocker rather than substituting an stdio result.
