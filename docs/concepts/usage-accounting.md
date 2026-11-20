# Usage accounting

PF records token counters and observed agent execution intervals in one local
workplace database: `data/accounting/accounting.sqlite3`. The configured
workplace is resolved through the project's existing local manifest reference.
There is no checkout, installation or cache fallback. Collection requires an
explicit `project.id` from the PF manifest. All projects and future clients use
the same `AccountingService`; project mappings and a stable local origin are
persisted beside the database. Project names and current directories are not
identities. Explicit imports retain their declared original origin/source ids.

```sh
python bin/pf.py usage summary --project-root <project> --json
python bin/pf.py usage projects --project-root <project> --scope workplace --json
python bin/pf.py usage project --project-root <project> --json
python bin/pf.py usage task --project-root <project> --task <assignment> --json
python bin/pf.py usage run --project-root <project> --run <run> --json
python bin/pf.py usage attempt --project-root <project> --run <run> --task <assignment> --attempt 1 --json
python bin/pf.py usage details --project-root <project> --kind activity --json
```

Queries always return JSON. Scope defaults to the selected project. A local
human CLI may explicitly choose `--scope workplace`; managed worker invocations
cannot expand to that scope. Transports must supply their own authorized project
set to `AccountingService`; command-line scope selection is not an authentication
mechanism. `--project-id`, `--task`, `--run`, `--attempt`, `--source-id`, `--model`,
`--start`, `--end`, `--limit` and `--offset` select/filter results. UTC windows are
half-open. Limits are 1–500; offsets 0–1000000. Summaries are not paginated.

Queries use read-only Core snapshots and do not create the database or local
origin. A missing store returns `status: unavailable`, `totals: null` and explicit
coverage. Unobserved counters are null; a measured zero remains zero. Cache
counters are subsets of input, not extra tokens. Reasoning counters are unknown
unless independently supplied by a supported source. Public service DTOs omit
private receipt locations and provenance hashes. `as_of`, source freshness and
coverage describe observed/declared sources only, never all device activity.

## Managed Codex capture

The driver runs `codex exec --json` while preserving `-o` final-report delivery,
heartbeat and subprocess exit. Each attempt has a distinct `usage-attempt-N`
directory below its native run directory, with `codex.jsonl`, `binding.json`,
`timing.json` and collection outcome/error metadata. Prior attempt directories
are never truncated. JSON stdout streams directly to disk; it is not accumulated
in memory. Collection happens after exit, including a failed exit. If storage is
unavailable, raw receipts and bounded safe error evidence remain for replay;
accounting errors do not replace the worker exit code.

Codex `turn.completed.usage` maps `input_tokens`, `output_tokens`,
`cached_input_tokens`, `cache_write_input_tokens` and `reasoning_output_tokens`.
Cache and reasoning counters are subsets, not additional tokens.
Ordered physical occurrences in the dedicated attempt
stream have distinct ids even when their payloads match. Absent native event
timestamps use the explicitly pinned source observation time with partial
quality. This timestamp is an observation, not a demonstrated request boundary.

The driver measures one monotonic execution duration for the attempt. Raw UTC
start/finish are retained. If UTC span and monotonic duration disagree, the
normalized interval retains both observed UTC endpoints and the independent
monotonic duration, with clock quality and discrepancy exposed. Calendar clipping
of a discrepant duration is unknown; UTC occupied time uses only observed forward
endpoints. Abrupt termination may leave an open timing receipt;
no tail is extended to query time. Ledger presence and child intervals are not
added to this attempt interval.

## Explicit collection/import/replay

These three command names perform the same bounded, checkpointed operation:

```sh
python bin/pf.py usage import --project-root <project> --file <receipt.jsonl> --binding <binding.json> --json
python bin/pf.py usage replay --project-root <project> --file <codex.jsonl> --binding <binding.json> --timing <timing.json> --json
```

The caller must have permission to read the exact files and must establish the
binding before import. A manifest is an explicit operator/managed-driver
assertion, not evidence automatically inferred from arbitrary source payloads.
No automatic session/history discovery is provided. Files are at most 64 MiB,
JSONL records at most 1 MiB, binding/timing metadata at most 64 KiB. Larger
sources need deliberately qualified segments with stable independent source ids.
Receipts and cursors commit in batches of at most 100 lines in one transaction.
The cursor pins the accepted prefix and binding. Repeating an unchanged source
does not duplicate facts. A changed/truncated prefix is rejected; malformed or
torn input returns an explicit error while retaining only the valid prefix.
Appending the completed tail resumes collection. Never reuse a source id for a
rotated, rewritten or different stream. Retain the original `observed_at` on
replay. A semantic revision is a separate Core ingest operation, not rewriting
an imported stream.

Synthetic binding example (replace every asserted identity with qualified data):

```json
{
  "schema_version": 1,
  "primary_records": true,
  "origin_id": "explicit-stable-origin",
  "source_id": "explicit-stable-primary-stream",
  "profile": "kimi-code-2.3.0-v1",
  "observed_at": "2026-10-22T12:00:00Z",
  "attribution": {
    "project_id": "example",
    "agent_instance_id": "agent-1",
    "session_id": "session-1",
    "provider": "kimi",
    "model": "qualified-model"
  }
}
```

Work binding is optional. If supplied, `run_id`, `assignment_id` and positive
`attempt` must all be present and demonstrated; a session/project-only source
remains project usage without task attribution. Unknown model may be omitted.

## Modern Kimi profile and qualification

The initial profile targets the modern TypeScript `kimi-code` 2.3.0 counters,
not legacy Python `kimi-cli`. Explicit import accepts a **PF qualified projection**
of primary wire occurrences, not arbitrary native wire layouts. The upstream
occurrence/session identity, primary provenance and project/Work association
must be established by the importer. Synthetic JSONL example:

```json
{"type":"usage.record","primary":true,"occurrence_id":"native-request-1","session_id":"session-1","agentId":"agent-1","model":"qualified-model","usageScope":"session","timestamp":"2026-10-22T12:00:00Z","usage":{"inputOther":40,"inputCacheRead":20,"inputCacheCreation":10,"output":3}}
```

Input total is the sum of all three input components **only when all are
present**. Session scope neither excludes a record nor proves a cumulative
snapshot. Qualified primary deltas contribute once by stable occurrence id;
summary/status mirrors and parent copies of child usage must not be projected
as new primary facts. Repeated identical occurrences deduplicate; conflicting
payloads under one occurrence id fail atomically. PreCompact `token_count` and
`estimated_token_count` are never usage. The profile
`kimi-cli-legacy-unsupported` records explicit unsupported coverage without
reading/normalizing a legacy history.

Tests include synthetic edge cases and a sanitized real managed Codex terminal
receipt. Modern Kimi mapping is source-qualified and tested synthetically; native
Kimi capture and general provider/subagent completeness remain unqualified.
Collection status conservatively remains partial;
even successfully exhausting a file returns `complete: false`.

Exit codes: 0 successful query/import, 1 invalid input/scope/unavailable store,
2 explicit partial-input/unsupported collection error, 3 replay conflict. A
missing store query is successful with an unavailable envelope. MCP, TUI,
plugins and REST are future clients of the same scoped service DTOs.
