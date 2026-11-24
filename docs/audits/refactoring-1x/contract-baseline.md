# RF14 native contract baseline

Run these probes before an affected Core ownership change. Use the same probe
checkout on native Windows and native Linux. Each probe launches the selected
distribution's own entry in disposable fixtures. Install the Python
requirements and the tools listed in the [Python QA guide](../../../tools/python-qa/README.md).

## Select the target

Run from the probe checkout root. Use a separate target distribution. Obtain
the official ZIP and its sidecar manifest with their original filenames. Set
`PF_CONTRACT_ARCHIVE` for every profile because each driver checks the same ZIP.

| `PF_CONTRACT_PROFILE` | `PF_CONTRACT_ROOT` | Target identity |
| --- | --- | --- |
| `published-1.3.0` | Extracted official 1.3.0 ZIP | Source commit `804c53a775b963aceddc5759f8d94a8ed4b8d533`, tree `10e41b987223c6c5ec98b723eeb473e5e0e7df5d`. ZIP SHA-256 `80a4f15b1f4cfdce66dec44d15fbc9a9cc1fd615d8dc4c9c75ab872be679684a`. Sidecar SHA-256 `7c338d0546c3c081cf7b568a79922caa8ef4cc0f76f4b2cdd3039a1b21442518`. |
| `post-119-120` | Clean source checkout | Commit `336b61d470c2a68b4091e6667921a22ecf135ce5`, tree `db45ebc46e34f3c4ef4da6ae376657ff0561f2b8`. |
| `candidate` | Clean checkout of the revision to qualify | Set `PF_CONTRACT_EXPECTED_COMMIT` to its full commit ID. Retain the tree from the fixture output. The development base is `ebf0a52b573f0ee1f769a2c2df3659a0a4411ebd`, tree `0650894878cffc1b2e67588ec990fe4252e73caf`. |

Linux invocation for the published profile:

```sh
export PF_CONTRACT_PROFILE=published-1.3.0
export PF_CONTRACT_ROOT=/path/to/extracted-distribution
export PF_CONTRACT_ARCHIVE=/path/to/processforge-1.3.0.zip
export PYTHONPATH="$PWD/tools:$PWD/src:$PWD/tests"
python3 -m pytest -p no:cacheprovider -s tests/refactoring_contracts
```

Windows invocation for the published profile:

```powershell
$env:PF_CONTRACT_PROFILE = 'published-1.3.0'
$env:PF_CONTRACT_ROOT = 'path\to\extracted-distribution'
$env:PF_CONTRACT_ARCHIVE = 'path\to\processforge-1.3.0.zip'
$env:PYTHONPATH = "$PWD/tools;$PWD/src;$PWD/tests"
python -m pytest -p no:cacheprovider -s tests/refactoring_contracts
```

Repeat with `post-119-120` and `candidate` and their verified roots. The fixture
marks a candidate run without `PF_CONTRACT_EXPECTED_COMMIT` as exploratory.
An ordinary local pytest run without archive inputs omits the two archive
probes. Explicit matrix runs require the ZIP and sidecar for every profile.
Use a fresh short disposable base with `--basetemp` if needed. Pytest clears
that directory at startup. Retain evidence before reusing it.

Replace `tests/refactoring_contracts` in the command above to run one lane.

| Lane | Pytest path |
| --- | --- |
| Entry and Runtime | `tests/refactoring_contracts/test_cli_runtime.py` |
| MCP | `tests/refactoring_contracts/test_mcp.py` |
| Work and search | `tests/refactoring_contracts/test_work_search.py` |
| Storage and archive | `tests/refactoring_contracts/test_storage.py` |

## Entry and Runtime

In these commands `pf` and `pf-server` mean the selected Windows `bin\pf.bat`
and `bin\pf-server.bat` wrappers or Linux `sh "$root/bin/pf"` and
`sh "$root/bin/pf-server"`. The paired Python entries are
`python "$root/bin/pf.py"` and `python "$root/bin/pf-server.py"`.

| Case | Command or request | Expected result |
| --- | --- | --- |
| Version | `pf version` | Exit 0, version text, empty stderr. |
| Runtime absent | `pf runtime status --workplace <absent> --json` | Exit 0, JSON stdout with top-level `status: not_running` and `health: stopped`, empty stderr, Workplace still absent. |
| Server absent | `pf server status --workplace <absent> --json` and `pf-server status --workplace <absent> --json` | Exit 0, JSON stdout with `runtime.lifecycle: not_running`, empty stderr, Workplace still absent. |
| Configuration refusal | `pf server run --workplace <malformed>` and `pf-server run --workplace <malformed>` | Exit 1, empty stdout, stderr `FAIL: configuration_yaml_invalid`. The fixture still contains only its malformed `configuration.yaml`. |
| Lifecycle | `pf-server start --workplace <fixture> --interval 60 --timeout 30 --json`, repeat through `pf runtime start`, then read `pf runtime status` and `pf server status` | Both entries identify the same ready instance. Readiness returns HTTP 200, an unauthenticated event returns 401, and readback after shutdown reports `stopped`. If `pf-server stop` reports the guarded 409 refusal, check the exact reason and stop the same fixture through `pf runtime stop`. |
| Native results (#119) | Run `check_concurrent_native_actions` from `tools/smoke_long_lived_runtime.py` against the selected Forge fixture. Register the sessions, then send concurrent `POST /mcp` calls for two `pf.session.heartbeat` requests with `apply: true` and one `pf.runtime_driver.describe` request with `driver: unregistered`. Send `POST /tick` for the same project with Director and Inspector enabled. | HTTP 200 for each exchange. Each fixed heartbeat's `native_summary` identifies its agent and session. The describe request returns `isError: true` and `driver_not_registered`. Both scheduler components report `tick`. Record the method and arguments with the wire ID because one heartbeat and the refusal share an ID. |

On the published ZIP, native Windows status calls observed the two distinct
JSON shapes in the table. Direct invocation of the extracted POSIX wrapper
on Linux returned permission denied with its supplied mode `100644`. Preserve
that observation alongside the `sh` rows. For #119 record the actual
published exchanges. The published adapter redirects process-wide streams.
Observed outcomes include the expected heartbeat, text from another action,
and a correctly correlated tool error with code `read_failed`. The fixed
profiles require the two exact heartbeat summaries.

## MCP bridge

Start the selected bridge with the fixture environment. Use separate Garage
and Forge fixtures and keep each sequence on one initialized connection.

```sh
python -B "$root/tools/pf_runtime/mcp_server.py" --workplace "$workplace" --session "$session"
```

| Case | Wire operation | Expected result |
| --- | --- | --- |
| Discovery | `initialize`, `tools/list`, `resources/list` | Valid envelopes with matching request IDs. Both Work names advertise their respective schemas. |
| Project Work projection | `tools/call` for `pf.work_state` with `project_root` and `session_id` | Project, Work, context and session projections agree with the fixture binding. |
| Exact Work | `tools/call` for `pf.work.state` with `project_root`, `session_id`, `run_id`, `assignment_id` and `context_id` | Selects the exact identity and refuses a mismatched selection. Retain the JSON-RPC error, tool error or blocked result actually returned. |
| Compatible replacement | Repeat discovery and a read after replacing Core in a disposable consumer. Exercise discovery subscriptions. | Same bridge PID, changed Core identity, refreshed discovery and corresponding subscription notifications. Use coherent publication bytes for a sealed consumer. |
| Backend unavailable | Attempt one mutation across backend loss, then read after recovery. Include a Forge Runtime-unavailable read. | On an indeterminate mutation record one attempt, `outcome: unknown` and `automatic_retry: false`, then the later read. |

Run the initial published wire sequence from the unchanged extracted release.
Record published replies separately from post-fix and candidate replies. Use
disposable copies for replacement and outage tests.

## Work and search

The probe seeds two generations with the same resource ID and filenames and
distinct body markers, plus a sibling project. It runs
`python "$root/bin/pf.py" search-index-maintain --workplace "$workplace" --apply --json`
and drives the selected stdio entry.

| Case | Wire operation | Expected result |
| --- | --- | --- |
| Project selection (#120) | `tools/call` for `pf.search` with `project_root`, `query`, `limit` and `offset`, then `pf.resolve` with the matching `resource_id` | The fixed profiles filter to the selected instance before totals and pagination. Record the selected version and root, exclusion of the other marker, total, page results and resolved material bytes. |
| Work selection and pinned material | `tools/call` for `pf.work.start` with fixture `project_root` and `objective`, then `pf.work.state`, `pf.work.search` and `pf.work.resolve` with the returned selectors and applicable query or resource ID | The Work identity remains pinned. Record `work`, `resource_provenance`, `coverage.source` and the material result independently of project search. |
| Denial and replay | `tools/call` for `pf.work.transition` with explicit `run_id`, `assignment_id`, `context_id`, `outcome` and stage `evidence`. Exercise denial and replay the accepted request. | Compare identity, stage, evidence count, journal event IDs and sibling-project state. The Forge bridge test correlates the outbox delivery receipt with the committed event ID. |

The supplemental native Windows Core probe returned four shared matches and
two other-version matches for the published driver. The post-fix and
development-base drivers returned two selected-version matches and zero
other-version matches. Published pagination continued past the second page.
Fixed pagination ended there. This probe used synthetic project snapshots.
The native Work/search test retains each public request and its correlated
reply from both projects in fixture-local `project-*-search.json` files.

## Storage and archive

Run against a fresh disposable Workplace and project.

```sh
python "$root/bin/pf.py" workplace-init --workplace "$workplace" --apply
python "$root/bin/pf.py" project-init --project-root "$project" --workplace "$workplace" --type generic --coordination-mode simple --process task-batch-execution --apply
python "$root/bin/pf.py" run-create --project-root "$project" --id "$run_id" --title "Journal persistence probe" --process task-batch-execution --apply
python "$root/bin/pf.py" project-init-status --project-root "$project" --workplace "$workplace" --json
```

Require exit 0 at each step. The isolated fixture reports
`workplace: reachable`, a current Agent Entry, and an empty
`missing_deterministic_artifacts` list. Its status and snapshot health are
`blocked`. Read `pf_store_meta.store_id` from
`.pf/runtime/events/events.sqlite3` in SQLite `mode=ro` after initialization.
After the native event call, record `events.event_id`, `event_type: run.created`
and `subject: <run_id>`. Reopen after status and compare the event and UUID.

The archive probe verifies the driver's copied bytes before executing from its
disposable copy. It validates the archive and sidecar through the selected
driver, then verifies the extracted bytes and invokes the published CLI in
the extraction. Set `TMPDIR`, `TMP` and `TEMP` to owned extraction scratch.

```sh
python "$driver/bin/pf.py" release-archive-test --archive "$archive" --manifest "$manifest" --extracted-test skip
python "$extracted/bin/pf.py" release-test --root "$extracted" --only "schema validation" --only "public cleanliness" --only checksum
```

Require exit 0 and `RESULT: PASS` from the manifest check. Require exit 0
and all three named checks from the extracted CLI. Its only expected warning
is that the extracted archive lacks Git metadata for `git diff --check`.
Retain both transcripts and recheck the driver reference, archive and
sidecar bytes. Run a refusal with `--extracted-test quick` and a disposable
manifest copy whose `archive.sha256` differs. Require exit 1, the archive SHA
mismatch diagnostic, no extraction and no new driver evidence. The broader
extracted quick smoke additionally starts a Runtime. Two native Linux
published runs observed its guarded shutdown refusal.

## Evidence and review

For every case record the command, platform, effective target, harness commit,
fixture SHA-256, typed exit or wire outcome and the proof location. Record the
archive and driver identities separately. Keep raw streams and wire exchanges
private and exclude bearer credentials. Normalize fixture paths, timestamps,
PIDs and generated IDs after verifying their types and associations. Preserve
failed observations and corrected reruns. Record unavailable rows as open.

Final review covers the exact candidate commit and tree, the entire candidate
diff and its callers, and all three profiles on native Windows and Linux.
Repository CI remains a separate gate.
