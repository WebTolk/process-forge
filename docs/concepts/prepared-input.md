# Prepared worker input

Strict v2 egress Work enters the [managed broker](egress-engine.md). Native
preparation rejects it with `enforcement_unavailable` before copying source
material into a worker prompt. Existing v1 preparation remains unchanged.

Prepared input is the private, bounded delivery package for one validated assignment context and one attempt. ProcessForge builds it from the current ready execution contract, pinned capsule and snapshot, required sources, outputs and currently authorized resource grants. It does not create a second Work or let the worker choose a newer process, stage, source, or permission set.

The version 1 shape is defined by [`prepared-input.schema.json`](../../schemas/prepared-input.schema.json). A manifest is stored under the attempt's private runtime directory as `attempts/<attempt>/prepared-input.json`; the command and run state retain its project-relative path and `sha256:` checksum. The top-level project root is private runtime metadata. Do not copy it or resolved workplace paths into public artifacts.

## What the manifest contains

The envelope identifies `kind: pf.prepared-input`, `visibility: private_runtime`, the project/run/assignment/context and attempt, the complete prepared `input`, its fingerprint, an output baseline, and fixed inline/JSON ceilings. The input contains the objective, capsule path and byte/contract/intent checksums, pinned snapshot and process, current stage view, explicit scope/actions, output/report obligations, source records, capabilities, parameters, subagent policy, and resource grants.

The manifest is written once per attempt. Its overall UTF-8 JSON ceiling is 4 MiB. Required text inputs may include at most a 64 KiB prefix per file and 256 KiB total. An oversized or non-text input is represented by its checked project-relative reference and checksums; ProcessForge does not copy a full source tree into the prompt. Preparation checks the source's declared checksum and read scope before delivery. A larger source still needs a valid declared reference and worker authorization to read it.

Atomic publication uses a flushed temporary file and an exclusive hard link in the same directory. The runtime filesystem must support hard links; unsupported publication fails explicitly instead of leaving a partial final manifest or overwriting an existing one.

T02 resource-material verification retains its own fixed ceilings: 64 resources, 2,048 files and 32 MiB overall; 20,000 visited entries; 256 files and 8 MiB per resource; 1,000,000 bytes per file; and 2,048 generated documents / 32 MiB of generated searchable content. These limits bound resource verification and derived material, not permission to access a directory. They can cause preparation to fail before a worker starts.

A knowledge grant marked `metadata_only` contains navigation metadata and no resolved body path. It does not authorize reading the resource body or its containing root. Full-text knowledge is checked against the pinned binding, current project authorization and stage subset; the private manifest records portable references, provenance and bounded file hashes. Templates, tools and MCP grants are also matched to pinned/current selections and resolved before launch. A registry entry by itself grants nothing.

Explicit tool grants use the selected registry ID. The public snapshot keeps
only its portable `path_ref` (`registry: tools`, `id`) and a
`definition_fingerprint`: SHA-256 of the complete authoritative definition,
serialized as UTF-8 JSON with sorted keys, compact separators, Unicode preserved
and non-finite numbers rejected. Commands, private paths, status and restrictions
are covered by the digest; commands and private paths are not copied into the
snapshot. Prepare and start check pinned/current selections and reread the unique
current registry record, including revocation and drift without a refresh.

A file-backed tool retains the existing path containment and existence checks.
A command-only tool may instead receive `resolution.status: descriptor` with its
verified `entry`, including a nonempty command, only in the private prepared
input. This descriptor grants no directory or file-body access and adds no broad
Codex directory grant. Templates and MCP keep their existing file-backed form.
Missing references/digests, ambiguous or changed identities, changed definitions
and revoked records fail closed. Existing immutable snapshots/capsules are not
upgraded in place: new tool grants require a fresh governed context.

## Driver handoff and execution

Every prepared driver receives the reserved `PF_PREPARED_INPUT_FILE` and `PF_PREPARED_INPUT_SHA256` environment pointers together with `PF_WORKER_ATTEMPT`. Runtime drivers may not set these variables themselves. `runtime-driver.schema.json` describes the optional `prepared_lifecycle_wrapper` boolean and reserves these names. A driver opts into wrapper behavior through trusted driver configuration, not event data.

Manual preparation produces the same per-attempt manifest and prompt pointer but starts no process. The built-in generic-shell driver opts into `tools/prepared_executor.py`, which validates the manifest pointer, raw-byte digest, identity and size before starting the existing target argv with inherited stdin/stdout/stderr, working directory and environment. It records starting, periodic and final heartbeat state plus the durable exit contract. The wrapper does not bootstrap PF or MCP and makes no OS sandbox claim.

Codex uses its existing `tools/codex_exec_worker.py` wrapper and consumes the same prepared manifest. The launch prompt directs it to verify the path and checksum, use only inline content and declared file references, avoid rebuilding context or starting another Work, and treat metadata-only grants as metadata only. For a prepared launch, Codex does not receive broad `--add-dir` grants from workspace-access paths. Generic prepared execution does not require an MCP connection or network access; this statement does not constrain what an executable can do unless its operating-system sandbox enforces it.

In prepared mode, Codex receives fixed instructions and the verified manifest only. It does not read the mutable worker prompt, capsule body, or workspace-access pointer. A worker assignment must declare `expected_report.artifact` and matching write scope before immutable context is created. An ordinary primary Work with no declared outputs is not worker-ready and fails with `worker_report_undeclared`; ProcessForge does not infer authority from a filename.

Immediately before launch, ProcessForge reloads and checks the attempt file and checksum, exact Work/assignment/context identity, capsule pins, input fingerprint, and current sources and authorization. A changed source, stale snapshot, revoked grant, or mismatched path blocks launch. The manifest is a delivery record, not a new authority source.

## Attempts, outputs, and collection

Each deliberate prepare uses a new attempt directory and never overwrites a prior manifest. It records each required output/report baseline (missing or present with checksum, size and timestamp) and increments the attempt; a failed/retried worker does not silently reuse the old attempt. The current driver `max_retries` setting is a limit/configuration field; retry is not an automatic loop. After `ready`, `start` reuses the same prepared attempt and exact saved command. Preference changes require an explicit new prepare. A blocked launch requires repair followed by explicit prepare before another start.

Collection revalidates the prepared context and requires required outputs, including the expected report, to exist and be attributable to the current attempt. The expected report is preflighted as UTF-8 and limited to 2 MiB before the receipt is committed; output files are limited to 8 MiB each and 32 MiB total. A non-UTF-8 or oversized report fails without committing a receipt, so it can be repaired and collected again on the same attempt. An unchanged file already present in the baseline is not accepted as this attempt's output. ProcessForge writes a per-attempt collection receipt that pins output bytes. Repeating collection with the same receipt returns the prior completed result; changed output bytes are rejected. Governed collection preserves the primary lifecycle; durable receipt/completion identifiers and dead-owner recovery support interruption recovery without duplicate completion events.

Automatic supervisor ticks distinguish an already completed capture from a fresh collection. A consistent private prepared-input, capsule, receipt and completion chain is reported as `historical_observed` and included in `observed`, never in `collected`. This observation reads the current bounded metadata, but does not reread source or output bodies, assert current authorization, accept the result anew, or complete the parent Work. Such an attempt needs no collection drain. Missing, inconsistent or unreadable proof takes the ordinary collection path. Explicit collection, first capture and interruption recovery retain the full current checks described above.

A first full collection can record an outstanding semantic refusal for that exact attempt. The recognized reasons are `required_source_changed`, `prepared_input_changed`, `prepared_input_context_mismatch` and `work_context_mismatch`, raised directly by the existing prepared-input checks. Arbitrary matching exception messages, filesystem/lock failures, invalid UTF-8 and unknown failures do not establish this observation. A private `collect-block-<progress-key>.json` binds the exact prepared bytes, identity, input fingerprint and capture-progress metadata. The short key only routes the lookup; the complete document must match. Every automatic observation rereads and checks that metadata. Changed capture progress permits full recovery and a separate refusal observation if that recovery encounters another stable semantic failure. Inconsistent, missing or unreadable proof retains full collection.

While a refusal is outstanding, supervisor reports `recovery_required` with task, attempt and reason, includes the task in `observed` and `failed`, and returns failure. It does not repeat the full collection, report a capture, or complete the parent Work. Restoring a source alone does not trigger automatic acceptance: use explicit `worker-run collect`, or prepare a new attempt. Explicit collect always retains full current checks. Successful capture takes priority over the old refusal; changed receipt/completion metadata also invalidates the old observation and allows full interruption recovery. A failed manual retry does not prove the previous semantic refusal resolved. Final drain remains visibly pending/failed instead of retrying the same full collection in a loop.

These are source-checkout contracts. Installed Core, Workplace and actual-host acceptance remain a separate T06 qualification; source schema validation or local smokes do not prove installed behavior.

See [Work context](work-context.md), [Work-scoped resource reads](work-resources.md), [context capsules](context-capsule.md), and [runtime drivers](runtime-drivers.md).
