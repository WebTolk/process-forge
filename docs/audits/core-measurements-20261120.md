# Two-device PF measurements and Core documentation audit

On 20 November 2026 the installed Windows RC1 completed a normal hook dry-run
in a median **1.319 s**. The beta3 device took **4.424 s**. Reading the first
100 events took **20.568 ms** on RC1 and **4.861 ms** on beta3. The bound
RC1 store required a storage host for this read. See the detailed report for
first calls, ranges, inventory, profiling and reproduction. [Full report in Russian](../ru/audits/core-measurements-20261120.md) · [Original beta3 report](https://github.com/WebTolk/process-forge/issues/110)

## Measured installations

| Observation | Windows RC1, 11:07–11:08 UTC | Windows beta3, 03:48–04:00 UTC |
| --- | --- | --- |
| Installed Core | `26226c26333be14267dafcfd165c3d0975ab76d2`, 1.3.0-rc1 | `076f153168ec257ee2d0a0c4f74d7031d6bf44b4`, 1.3.0-beta3 |
| CPython / SQLite | 3.11.9 / 3.45.1 | 3.14.3 / 3.50.4 |
| Event history | 14,418 rows, 47,181,824 bytes | 245,892 rows, 1,196,953,600 bytes |
| Hook journal | 4,695 receipts, 801 retained raw rows, 32,583,680 bytes | 89,527 receipts, 33,469 raw rows, 439,382,016 bytes |
| Codex handlers / project routes / enabled routes | 8 / 2 / 1 | 8 / 3 / 1 |
| Effective history settings | Events on, raw off | Events on, raw on |

The two SQLite journals used WAL with 4,096-byte pages. Transcripts and
telemetry used NDJSON, and diagnostics used rotating JSONL on RC1. The
additional bound execution store held 169 attempts. The beta3 device still
had a previous NDJSON event file with 86,054 nonempty lines. Migrated rows
can appear in both representations.

| Operation | Timed repeats | RC1 median, ms | Beta3 median, ms |
| --- | ---: | ---: | ---: |
| Dry-run, new CLI process, normal / diagnostic | 7 pairs | 1,319.195 / 1,308.925 | 4,423.802 / 4,424.594 |
| Same calls, logged duration, normal / diagnostic | 7 pairs | 1.481 / 95.942 | 4.962 / 531.764 |
| First page from the installed Core, 100 matching IDs | 20 | 20.568 | 4.861 |
| Connected MCP `pf.context` | 3 | 4,458, fresh | 47,863, stale |
| CLI `project-context-check` | 3 | 2,124.665, fresh | 10,978.236, refused |

All CLI dry-runs selected one outbox. Debug logging included a start record
inside the operation timer. The external ranges overlapped between profiles
on both devices. RC1 passed `events-validate` in 2.675 s. The beta3 validation
was interrupted at its 120 s deadline. RC1’s Forge context was usable while
Runtime doctor reported degraded health.

The extra RC1 page profile spent 1.266 s of its 1.336 s in storage identity
admission across 20 calls. On this adopted store the beta3 example using a
bare journal returned `storage_host_required`. Device, history, logging,
backend outcome and interpreter differ. The measurements do not isolate a
release or hardware effect.

## Documentation findings

The baseline was integration commit `a4ecea35a83e9c5b8d1f2f683714ee3b3268eba6`.
The review covered the two language trees, top-level guides and prompts
(404 Markdown files). All 945 checked relative path links resolved. The CLI
parser accepted 730 standalone shell examples in current documents. Fifteen
dynamic or help examples were excluded. These checks exercise names, paths
and grammar. The behavioral corrections below were traced to their owners.

- The workplace’s default mode controls Codex setup during initialization.
  Effective project mode and PFConfig govern collection at runtime. The
  provider registry also accepts Kimi input. [Setup](../../src/processforge_core/project/agent_hooks.py) · [Collection](../../src/processforge_core/agents/hook_admission.py) · [Adapters](../../tools/pf_runtime/builtin_provider_adapters.py)
- Project hook targets support dry-run and local outbox delivery. Command
  targets are skipped. Work files, bound execution state, optional raw history
  and private transcripts have distinct owners and formats. [Dispatch](../../src/processforge_core/agents/hook_dispatch.py) · [Storage initialization](../../src/processforge_core/maintenance/fresh_project.py) · [Transcript naming](../../src/processforge_core/chat/transcripts.py)
- The host owns the MCP transport. Garage starts a backend child per request.
  Forge routes to the running workplace Runtime. Work selectors and Ledger
  session identity serve different operations. [Bridge](../../tools/pf_runtime/mcp_bridge.py) · [Dispatcher](../../tools/pf_runtime/mcp_server.py)
- The CLI telemetry bootstrap records the requested mode and assignment reference.
  Onboarding a project and launching a worker have separate entry points. [Session bootstrap](../concepts/session-bootstrap.md)
- Invalid project diagnostic settings select `off/none`. The CLI uses both
  PyYAML and jsonschema, and the source CI matrix uses Python 3.11 on Windows
  and Ubuntu. [Diagnostics](../../src/processforge_core/diagnostics.py) · [Dependencies](../../requirements.txt) · [CI matrix](../../.github/workflows/repository-checks.yml)
