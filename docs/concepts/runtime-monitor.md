# Local Runtime monitor

`pf monitor` is a read-only terminal view of the existing workplace Runtime.
Closing it with **Q**, **Esc**, or **Ctrl+C** leaves the server running. It does
not start, stop, repair, install or configure any service.

From a source checkout (replace the example workplace with your directory):

```sh
python -B tools/processforge.py monitor --workplace ./workplace
python -B tools/processforge.py monitor --workplace ./workplace --once --ascii --no-color
python -B tools/processforge.py monitor --workplace ./workplace --json
```

The launcher also accepts `python bin/pf.py monitor ...` in distributions that
include this command. Updating a source checkout does not update an already
installed Core. `pf monitor --help` describes the available flags.

An interactive terminal follows the applied Runtime statistics interval (default
10 seconds), with a delay after each observation. `--interval` accepts finite
values from 1 to 60 seconds and overrides only the viewer. A legacy ready Runtime
without interval metadata keeps the old two-second viewer default. Without a
running Runtime the viewer uses the selected workplace configuration/default.
The compact view includes a small static PF splash, uptime, sample age and
activity counts; `--details` selects scheduler and observation diagnostics.
There is no splash delay. See [workplace configuration](../authoring/workplace-configuration.md)
for YAML, the independent Core CRUD API and CLI commands.
There are no overlapping probes or catch-up bursts. Resizing the terminal
reflows the view. Ordinary updates change only affected rows. A narrow/short
screen keeps the Runtime state first and omits lower-priority rows. Output is
monochrome; `--no-color` is supported. `--ascii`, or a non-UTF-8 output encoding,
uses ASCII text. Windows VT support is enabled only for the viewer's output
handle and restored on normal exit or handled errors.

`--once`, redirected output, missing terminal input or an unsupported terminal
produce a single plain snapshot. `--json` always produces exactly one JSON
object, without splash, color or cursor-control sequences. JSON uses escaped
Unicode and contains the same restricted projection, not a raw state dump.
Exit code 0 means an observation was produced, even if its state is offline or
unknown; 2 indicates invalid arguments; 1 indicates an internal viewer error.

## What the values mean

| Value | Source and limitation |
|---|---|
| Runtime lifecycle | Matching lock/state identity, a bounded PID observation and loopback readiness; orphaned/stale are not ready |
| Health | Saved Runtime health, shown as current only with ready lifecycle and fresh state |
| State age | `service.json` timestamp; stale after max(15, 2 × applied interval + 5) seconds; legacy threshold 15; missing, malformed or future time is unknown |
| Scheduler | Saved job results and their own freshness, not a live scheduler-thread health check |
| Registered projects / cached sessions | Host cache entries, with cache freshness; these are not active-work totals |
| Session presence | Agent Ledger online/stale/offline with heartbeat TTL; online does not mean busy |
| Reported workers | Running status records; not OS liveness |
| Work records | In-progress and blocked Runs; blocked does not mean waiting for the user |
| Leases | Held, expired and inactive records; not a conflict detector |
| Waiting for user, events, backlog, MCP and hooks | Unknown; no aggregate contract |
| CLI / instance versions | Version of the command being run versus the recorded Runtime instance; neither proves matching builds |

Readiness can coexist with degraded health. An unavailable probe or a changing
owner yields uncertainty rather than a false stopped/healthy result. `/readyz`
does not attest process identity cryptographically; lock/state rechecks are a
local consistency check. A PID alone is not proof of ownership.

The viewer reads only bounded service/lock/host-cache records. Service and cache
records are limited to 1 MiB each; lock records to 64 KiB; at most 32 scheduler
rows are shown. Oversized or unreadable data yields a reason such as
`cache_oversize` and unknown counts. It never scans project trees to fill in
missing values. These thresholds are observation policies, not a daemon
heartbeat guarantee; slow storage can legitimately exceed them.

New Runtime builds publish compact instance-bound `metrics` inside `service.json`
at the configured period, 10 seconds by default. Its own timestamp expires after
max(5, 4.5 × sample interval) seconds. Legacy samples without interval metadata
keep the 45-second limit. Invalid interval metadata cannot extend freshness.
Offline, changed-owner, stale or malformed snapshots cannot supply activity.
The viewer validates fixed fields and prefers compact registration counts to
the historical cache, including caches exceeding 1 MiB. Old servers retain the
unknown/fallback view.

Observation runs independently of the project scheduler. It reads at most
4 MiB of the existing registration cache and checks project manifest presence
without rebuilding context or replaying events. A long routing/tick pass cannot
delay publication; unreadable/missing project registrations leave coverage partial.

Each activity group has independent budgets: 512 visited entries, 128 files,
128 KiB per record, 4 MiB total, up to 128 project roots and one second checked
between filesystem operations. Fixed-depth traversal rejects symlinks/junctions.
Missing project coverage, malformed records or any limit produce `partial`:
exact JSON counts are null; `observed` and terminal `>=N` are lower bounds.
Canonical presence records supersede legacy duplicates. No journal scan occurs
per repaint. This is not an atomic cross-project transaction or a kernel IO deadline.
Collection is serial; overruns skip missed ticks and wait a full period. Runtime
reloads configuration at the next observation cycle; errors retain the last
valid value and appear as `configuration_invalid`. A fresh service heartbeat
does not refresh an old activity sample. Project context freshness remains a
separate per-project concept.

Readiness uses only numeric loopback HTTP, a 0.75-second overall network deadline
and bounded headers/body. Redirects, proxies, DNS destinations and tokens are
not used. PID observations are bounded on Windows. Filesystem access still
depends on the responsiveness of the selected local storage. This is not a
remote status client.

## Safety and operational boundary

The monitor does not create missing workplace directories, authentication
tokens, projections, logs or diagnostic output files. Generic diagnostic flags
do not enable writes for this command. Project names from records, session IDs,
prompts, raw errors, token values and local root paths are not rendered. The
chosen workplace's basename and approved version/PID fields identify the view;
terminal control characters in text are neutralized.

Normal exit restores the cursor and terminal mode. Killing the viewer
unconditionally may prevent terminal restoration, but cannot stop the server.
Server controls are separate commands: `pf server start|run|status|stop|restart`
or `python bin/pf-server.py ...`. `run --console` shows a banner only on a real
terminal; `status --json` uses this same read-only projection. Legacy `runtime`
commands remain compatible. These launchers run Python, not a native executable.

`server stop/restart` negotiate guarded shutdown with the current owner. The
server pauses admission while checking fresh worker records; running or unknown
workers, in-flight requests and an active scheduler pass refuse the stop.
Old servers without the capability also refuse. `--force` selects legacy
shutdown. The guard does not freeze independently launched CLI/MCP work.
Profile changes use `diagnostics-configure`, with preview and explicit `--apply`.
Closing the monitor never changes profiles. Tray/native packaging and remote
web remain separate work. See [Runtime MCP](runtime-mcp.md) and
[diagnostics](diagnostics.md) for their existing contracts.
