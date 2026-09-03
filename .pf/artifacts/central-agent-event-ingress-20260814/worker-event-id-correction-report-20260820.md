# Canonical PF worker event identifiers — 2026-08-20

## Result

PASS. Host now accepts worker conversation messages only with canonical PF-generated native event identifiers.

## Rules

- Input: `worker-input:<run>:<task>:attempt:<attempt>`.
- Output: `worker-output:<run>:<task>:attempt:<attempt>:<sha256 exact report content>`.

This prevents an otherwise valid worker payload from creating a second logical conversation message merely by changing an adapter-supplied native identifier.

## Validation

- `python tools/smoke_conversation_completeness.py` — PASS.
- The smoke rejects alternate input and output native ids with `untrusted_conversation_provenance`.
- `python tools/smoke_codex_exec_worker.py` — PASS.
- `python tools/processforge.py events-validate --project-root .` — PASS.
