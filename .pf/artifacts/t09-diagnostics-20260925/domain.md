# T09 domain and rules

Diagnostic is optional operational explanation, never required process evidence. Severity orders debug=10, info=20, notice=25, warning=30, error=40, critical=50, alert=60, emergency=70; canonical string is exported. Unknown level is an API error even on a no-op logger. Root Python logging is untouched.

Profile selects detail: quiet warning, normal info, diagnostic debug, trace debug plus bounded spans; off suppresses only optional events. Explicit threshold still applies. Configuration has schema version 1, effective values and per-field sources. Defaults < project < exact Work/session override < invocation; lower security/storage ceilings and locked fields cannot be relaxed. Detail ends at its absolute expiry or record allowance and returns to normal.

Correlation belongs to one invocation/attempt: real request/operation id, optional bound session and Work/assignment/run/attempt, snapshot and concrete Core/entry identity. Missing session is null, not synthesized. ContextVar binding prevents concurrent request leakage. Context only includes explicitly selected metadata, no automatic raw payload/prompt/env/content dump.

Sanitize before interpolation and every sink; sensitive keys and known secret values are removed, exceptions contain sanitized message/type and at most bounded frame metadata without locals/source. Unknown objects are represented by type, never unsafe repr. Config errors and optional sink failures are health signals and must not change business result. Serious event loss gets a bounded non-recursive stderr notice even if normal sink fails.

Private JSONL and stderr render the same canonical record. Optional records are bounded by byte size, depth/items/strings/stack/spans; only debug detail may be sampled/dropped by detail budget. Storage is bounded per project across processes. Read-only export accepts exact request/Work/time filters, copies only known diagnostic files with limits, redacts paths and secrets again, includes versions/effective config/snapshot/freshness/read-only status and manifest/truncation/redaction labels. Export creates only its requested artifact; it never repairs context or restarts a service.
