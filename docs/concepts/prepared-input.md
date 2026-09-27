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

## Driver handoff and execution

Every prepared driver receives the reserved `PF_PREPARED_INPUT_FILE` and `PF_PREPARED_INPUT_SHA256` environment pointers together with `PF_WORKER_ATTEMPT`. Runtime drivers may not set these variables themselves. `runtime-driver.schema.json` describes the optional `prepared_lifecycle_wrapper` boolean and reserves these names. A driver opts into wrapper behavior through trusted driver configuration, not event data.

Manual preparation produces the same per-attempt manifest and prompt pointer but starts no process. The built-in generic-shell driver opts into `tools/prepared_executor.py`, which validates the manifest pointer, raw-byte digest, identity and size before starting the existing target argv with inherited stdin/stdout/stderr, working directory and environment. It records starting, periodic and final heartbeat state plus the durable exit contract. The wrapper does not bootstrap PF or MCP and makes no OS sandbox claim.

Codex uses its existing `tools/codex_exec_worker.py` wrapper and consumes the same prepared manifest. The launch prompt directs it to verify the path and checksum, use only inline content and declared file references, avoid rebuilding context or starting another Work, and treat metadata-only grants as metadata only. For a prepared launch, Codex does not receive broad `--add-dir` grants from workspace-access paths. Generic prepared execution does not require an MCP connection or network access; this statement does not constrain what an executable can do unless its operating-system sandbox enforces it.

In prepared mode, Codex receives fixed instructions and the verified manifest only. It does not read the mutable worker prompt, capsule body, or workspace-access pointer. A worker assignment must declare `expected_report.artifact` and matching write scope before immutable context is created. An ordinary primary Work with no declared outputs is not worker-ready and fails with `worker_report_undeclared`; ProcessForge does not infer authority from a filename.

Immediately before launch, ProcessForge reloads and checks the attempt file and checksum, exact Work/assignment/context identity, capsule pins, input fingerprint, and current sources and authorization. A changed source, stale snapshot, revoked grant, or mismatched path blocks launch. The manifest is a delivery record, not a new authority source.

## Attempts, outputs, and collection

Each deliberate prepare uses a new attempt directory and never overwrites a prior manifest. It records each required output/report baseline (missing or present with checksum, size and timestamp) and increments the attempt; a failed/retried worker does not silently reuse the old attempt. The current driver `max_retries` setting is a limit/configuration field; retry is not an automatic loop. After `ready`, `start` reuses the same prepared attempt and exact saved command. Preference changes require an explicit new prepare. A blocked launch requires repair followed by explicit prepare before another start.

Collection revalidates the prepared context and requires required outputs, including the expected report, to exist and be attributable to the current attempt. The expected report is preflighted as UTF-8 and limited to 2 MiB before the receipt is committed; output files are limited to 8 MiB each and 32 MiB total. A non-UTF-8 or oversized report fails without committing a receipt, so it can be repaired and collected again on the same attempt. An unchanged file already present in the baseline is not accepted as this attempt's output. ProcessForge writes a per-attempt collection receipt that pins output bytes. Repeating collection with the same receipt returns the prior completed result; changed output bytes are rejected. Governed collection preserves the primary lifecycle; durable receipt/completion identifiers and dead-owner recovery support interruption recovery without duplicate completion events.

These are source-checkout contracts. Installed Core, Workplace and actual-host acceptance remain a separate T06 qualification; source schema validation or local smokes do not prove installed behavior.

See [Work context](work-context.md), [Work-scoped resource reads](work-resources.md), [context capsules](context-capsule.md), and [runtime drivers](runtime-drivers.md).
