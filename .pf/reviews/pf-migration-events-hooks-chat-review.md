# Review: PF Migration Events Hooks Chat

## Reviewed Object

`.pf` migration, process-owned events/hooks, WTAICC outbox payloads, and chat relay MVP.

## Result

pass_with_conditions

## Findings

- No blocking issues found in the implemented file-first model.
- `project-context-check` remains `HEALTH: warn` due to optional capability gaps. This is acceptable for the current MVP because `RESULT: pass` and `doctor-context` passes.
- `context-resolve` and `context-compile` still exist for compatibility. They are deprecated and no longer documented as the primary flow.

## Evidence

- `.pf/process-forge.yaml` is the active project manifest.
- `.pf/hooks.yaml` validates.
- Events validate under `.pf/runtime/events/events.ndjson`.
- Chat transcripts validate under `.pf/runtime/chat/transcripts/`.
- WTAICC outbox payloads are written under `.pf/runtime/hooks/outbox/wtaicc/`.
- Public cleanliness and checksum checks pass.

## Required Follow-Up

- Keep `--send` disabled until a future transport contract exists.
- Resolve optional capability warnings only if a process stage makes them required.
