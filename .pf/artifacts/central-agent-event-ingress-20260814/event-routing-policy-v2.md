# event-routing-policy-v2

Extracted verbatim in substance from the accepted architecture candidate `central-event-ingress-design-v2.md` so routing decisions have a durable standalone artifact.

## 1. Routing stages

Routing starts only after durable raw append.

```text
accepted raw
→ resolve session/project
→ normalize where meaningful
→ route to sinks
→ checkpoint
```

If routing fails, raw remains durable and replayable.

## 2. Project resolution

Resolution order:

1. Ledger session binding, if `source_session_id` is known.
2. Bootstrap lifecycle event with trusted `cwd`/`project_root` for `agent.session.started` or `agent.session.resumed`.
3. Explicit project ref from raw envelope, only after validation through Core project resolution.
4. Deferred if session/project cannot be safely resolved.

Never route an event into an arbitrary project because `cwd` exists in raw payload.

## 3. Mismatch policy

If Ledger says `session_id -> project A` and event requests project B:

```text
raw accepted = yes
project route = rejected
ledger write = no
chat write = no
diagnostic = project_session_mismatch
```

This preserves forensic data without cross-project contamination.

## 4. Sink policy

| Sink | Receives | Rule |
|---|---|---|
| Workplace raw journal | every accepted native event | mandatory |
| Workplace normalized journal | normalized facts | optional first slice, required later |
| Agent Ledger | lifecycle/activity facts only | after normalization and route validation |
| Chat transcript | provider message content only | through ChatService |
| Project events.ndjson | selected project-relevant normalized events | never raw dump |
| Projections/work-state | derived events | rebuildable, not ingress owners |
| Hooks outbox/results | outbound delivery only | not inbound raw storage |

## 5. Current semantics preservation

The first implementation slice must preserve the current observable behavior for supported Codex events:

```text
SessionStart startup/resume → Ledger check-in + project event
SessionEnd → Ledger checkout + project event
PostToolUse Bash → agent.command.completed + heartbeat when presence exists
PostToolUse non-Bash → agent.tool.completed + heartbeat when presence exists
```

Dedupe must prevent duplicate project events, Ledger activity, and chat messages on repeated delivery.

## 6. Unknown and raw-only events

Unknown provider events:

```text
raw journal = append/dedupe
normalized event = none unless generic diagnostic is explicitly enabled
project journal = none
replay status = pending/unsupported_mapping
```

This is required for future provider fields and new hook types.

## 7. Offline and replay

Runtime unavailable must not lose hook events. Direct fallback writes to the same raw journal and uses the same idempotency keys.

Replay rules:

- do not rewrite the same raw record;
- re-run normalization by version;
- route only missing derived records;
- use deterministic normalized ids derived from `raw_event_id + normalizer_version + semantic target`;
- support replay after Ledger resolution for previously deferred events.

## 8. Privacy and release boundary

Raw/chat streams are private runtime data:

- not tracked by git;
- not copied to release archives;
- not written into public artifacts;
- not sent to outbound hooks unless an explicit export path requests sanitized/full content;
- not logged in operator diagnostics.

`transcript_path` is provenance/recovery metadata only. It must be validated and must not be parsed as canonical input unless provider contract makes that format stable.

## 9. Acceptance tests for the future implementation

Required focused tests:

- every confirmed Codex native event raw-captured;
- unknown native event raw-captured;
- malformed envelope rejected before receipt;
- oversized payload rejected safely;
- concurrent writers preserve NDJSON line integrity;
- duplicate delivery does not duplicate normalized/project/chat records;
- unresolved session raw-captured but not misrouted;
- project A event never lands in project B;
- Runtime down path and Runtime up path produce equivalent durable results;
- replay after crash after raw append completes derived routing without duplicates;
- raw/chat files remain private and absent from release/public artifacts.
