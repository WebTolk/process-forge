# Global Agent Section

ProcessForge does not own a workplace-level `AGENTS.md`, `CODEX.md`, or similar
instruction file. It inserts or updates only a bounded navigation section:

```markdown
<!-- PROCESSFORGE:START -->
...
<!-- PROCESSFORGE:END -->
```

The section explains when PF applies and points to root `AGENTS.md` and
`.pf/process-forge.yaml`. An unmigrated project without root entry explicitly
uses `.pf/AGENTS.md`. Verify context through `pf.context`; a stored snapshot or
START file does not establish current authority. See
[session bootstrap](session-bootstrap.md) for the returned Work/capsule path.

Existing instructions outside the markers are preserved. Repeating the update
is idempotent. This global section is a navigation aid, not the minimum contract
K or evidence that the client loaded it.

```bash
python bin/pf.py global-agents-section --path <agent-file> --dry-run
python bin/pf.py global-agents-section --path <agent-file> --force
```

## Client Routes

Do not generate a generic pointer file for every vendor. Select one supported
route using the [entry profile and adapter policy](agent-entry.md). Clients with
an applicable root AGENTS loader need no vendor file. Explicit Claude/Gemini
native-import placement uses reviewed plan/apply; Aider gets read guidance;
OpenClaw prerequisites remain a separate observation. These operations do not
change host settings or start a client.

Merely linking to hidden instructions, printing a prompt or creating an adapter
cannot prove delivery, behavior or enforcement. K must reach the client through
the selected route within its effective instruction budget. Ordinary work uses
`pf.work.start`, `pf.work.state` and `pf.work.transition` without mandatory manual
session telemetry. Global user/device instructions remain applicable.
