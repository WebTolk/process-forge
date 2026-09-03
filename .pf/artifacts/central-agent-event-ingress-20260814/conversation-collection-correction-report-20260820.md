# Collectible worker report correction — 2026-08-20

## Result

PASS. The completed PF worker report is now captured as one assistant transcript message and collected by `worker-run collect`.

## Cause and correction

The report accurately said that `workspace-access` markers were withheld. The automatic-content filter rejected that harmless policy vocabulary, even though it contained no secret or local path. The filter now continues to deny actual local paths and secret values, while allowing safe discussion of withheld marker names.

## Validation

- `python tools/smoke_conversation_completeness.py` — PASS, including a collectible report that mentions the withheld `workspace-access` markers.
- `python tools/processforge.py worker-run collect --project-root . --task central-ingress-conversation-completeness-expanded-smoke-20260820` — DONE.
- The target worker session has one system input record and one assistant report record.
- `python tools/processforge.py events-validate --project-root .` — PASS.

## Privacy boundary

The capture still requires a PF-owned expected-report file whose exact content matches the raw envelope, a valid worker attempt, and an allowlisted provenance. Project-visible events remain metadata-only; actual secret values and absolute local paths remain denied.
