# Optional diagnostics

ProcessForge diagnostics are optional operational detail. They help explain a request or identify a local failure; they are not process facts, audit evidence, or a replacement for the mandatory event journal. Setting diagnostics to `off`, disabling a sink, or losing a diagnostic record must not suppress a required event, change an operation's result, or hide an explicit error.

## Configuration

The project file is `.pf/diagnostics.json`; its version 1 shape is defined by [`diagnostics.schema.json`](../../schemas/diagnostics.schema.json). A minimal example:

```json
{
  "schema_version": 1,
  "profile": "normal",
  "sink": "jsonl",
  "work": {
    "run-example": { "components": ["mcp", "context"] }
  },
  "sessions": {
    "session-example": { "threshold": "warning" }
  }
}
```

`work` is keyed by exact run id and `sessions` by exact session id. Each value may override the same settings as the project layer, including `locked`. The resolution order is defaults, project, matching Work, matching session, `PF_DIAGNOSTICS` JSON, then command invocation options. A `locked` field prevents later layers from changing that setting. Limits can only be lowered from the current layer's value. Invalid configuration uses the safe quiet/stderr fallback and reports a health/configuration error; it must not change the business operation.

The profiles set detail defaults: `quiet` uses `warning`; `normal` uses `info`; `diagnostic` and `trace` use `debug`; `off` disables optional diagnostics. A threshold includes that severity and all more severe levels. The canonical levels and Python numeric mapping are:

| Severity | Python value |
|---|---:|
| debug | 10 |
| info | 20 |
| notice | 25 |
| warning | 30 |
| error | 40 |
| critical | 50 |
| alert | 60 |
| emergency | 70 |

Python's standard levels keep their normal values; `notice`, `alert`, and `emergency` use the ProcessForge mapping. ProcessForge does not reconfigure Python's root logger. Components are optional filters; an empty list includes all instrumented components. Available sinks are `jsonl`, `stderr`, `both`, and `none`.

Detailed collection (`diagnostic`, `trace`, or a `debug` threshold) requires an absolute ISO 8601 `expires_at` with a timezone, no more than 15 minutes ahead. `Z` and numeric offsets such as `+00:00` are accepted; expiry is compared as a UTC instant. Invocation options that enable detail receive a bounded temporary expiry. Collection returns to normal when the expiry or detail-record ceiling is reached. Do not store a reusable future expiry in the project file; set it for a bounded investigation. `PF_DIAGNOSTICS` contains a JSON settings object and is an invocation layer. CLI settings are also invocation overrides.

Hard defaults, which configuration can only tighten, are: record 16 KiB, string 2,048 characters, nesting depth 6, 32 items per container, 8 stack frames, 32 spans, 1 MiB per JSONL file, 8 MiB total, 8 files including the active file, 7-day retention, 10,000 detailed records, and 64 KiB per config input. Lower record/file/quota limits must still fit together. Debug sampling defaults to every record and may be increased with `sample_every`.

## CLI surface

Global options go before the subcommand:

```text
pf --diagnostic-profile diagnostic --diagnostic-threshold debug --diagnostic-components mcp,context --diagnostic-sink both diagnostics-status --project-root .
pf diagnostics-status --project-root . --run-id example-run --session-id example-session
pf diagnostics-export --project-root . --output diagnostics-export.json --run-id example-run
```

The run and session filters on `diagnostics-status` are optional. Export can also filter with `--request-id`, `--since` and `--until`; replace example identifiers and timestamps with the intended values, and choose a new output file.

These commands are implemented in the source tree. Their availability still depends on the Core distribution actually being invoked: source checkout contents do not prove that an installed distribution contains the same implementation. Record the selected source/release identity when comparing behavior; an installed update or restart is outside this runbook.

`diagnostics-status` is an inspection operation: it shows effective values and their sources, locks, configuration errors, expiry state, and bounded health counters for the current process. Each retained canonical record also carries a snapshot of the counters at the time it was written. `diagnostics-export` reads only ProcessForge diagnostic JSONL, filters by request/run/time, sanitizes a local bundle, and creates the requested new file without overwrite. It does not repair context, restart a service, or upload data. Check the intended recipient and inspect the sanitized result before sharing it.

If configuration is invalid, collection fails closed to `off`; a fixed, non-sensitive health notification may still be written to stderr so operators can discover the fallback. It does not include rejected configuration values and does not bypass a locked sink or privacy policy.

## Privacy and failure behavior

`pf diagnostics-configure --project-root . --profile diagnostic --duration 120`
previews a profile change; repeat with `--apply` to persist it atomically in
`.pf/diagnostics.json` v1. Select at most one exact `--run-id` or `--session-id`;
otherwise the project layer changes. Other scopes/settings are preserved.
Existing locks apply even to the edited layer; malformed, linked or oversized
configuration is rejected. `diagnostic`/`trace` expires after 1..900 seconds
(default 600); other profiles clear the selected layer's expiry. Environment
and invocation precedence appears in the effective preview. Planning creates
no logs, locks or directories; apply serializes edits. Existing processes retain
their resolved configuration until their normal lookup; this is not a remote
live reconfiguration protocol. Mandatory process events are unaffected.

By default, diagnostics omit prompts, raw payloads, environment data, and file contents. Secret-like keys/values are redacted before sinks; local records may contain local operational paths, while export replaces absolute paths with a private-path marker. Context and messages are bounded by size/depth/item limits. Export is bounded to 4 MiB of input and output and at most 2,000 records; malformed or oversized records are rejected or marked truncated in the manifest.

The default private JSONL family is under `.pf/runtime/diagnostics/`; stderr is also available. Health counters expose emitted, filtered, dropped, truncated, serialization-failure, sink-failure, and detail-expiry information for the current process. Each retained canonical diagnostic record includes a counter snapshot. A bounded stderr warning signals loss of serious optional diagnostics. This signal is not a substitute for the required process journal, whose event names, severity values, deduplication, and failure semantics remain separate.

`PF_CODEX_HOOK_DEBUG=1` enables a temporary detailed hook diagnostic profile. It emits canonical sanitized diagnostic records to stderr; hook protocol stdout remains unchanged. It does not dump the raw hook payload or result.
