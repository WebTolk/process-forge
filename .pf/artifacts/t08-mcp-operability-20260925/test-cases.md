# T08 — выполненные сценарии

| ID | Действие | Ожидаемый и фактический результат | Evidence |
|---|---|---|---|
| C01 | Main host context + source/installed CLI checks | PASS: fresh, same ctx-20260925-140110-0dbc7c and CLI checksum, execution ready | host-context-after-restart.json; context-cli-parity-after-restart.json |
| C02 | Main host state vs source state | PASS: existing T08/code-assurance, same software process pin and two selected resources | host-work-state-resumed.json; final-verification.json |
| C03 | Host process identity and installed ownership | PASS: actual Python PID5044/launcher18788 uses installed mcp_server.py; all 954 hashes match | host-process-identity.json; final-verification.json |
| C04 | Fixture search gitverse + resolve | PASS: exactly one docs.api.gitverse:root metadata result, available/resolved root | fixture-search-positive.json; fixture-resolve-positive.json |
| C05 | Main resolve same resource | PASS: denied/not_in_project_snapshot | main-resolve-denied.json |
| C06 | Main session_context without session | PASS: missing_session with remediation, no invented session | host-missing-session.json |
| C07 | Host fixture start/state | PASS: created_new then same Run/Assignment at verify, session absent | fixture-work-start.json; fixture-work-state.json |
| C08 | Host transition with missing evidence file | PASS: transition_rejected/artifact_path_missing, verify unchanged, evidence empty | fixture-invalid-evidence.json |
| C09 | Host valid verify transition | PASS: stage_transitioned to finish; evidence hashes recorded | fixture-transition-verify.json |
| C10 | New installed stdio connection start/state | PASS: continue_existing exact host-created Run at finish, prior input satisfied, no duplicate | reconnect-proof.json |
| C11 | Host finish with actual completion evidence | PASS: run_completed, assignment done, completion complete | fixture-completed.json |
| C12 | Genuine fixture manifest change, then restore exact bytes | PASS: host search snapshot_not_fresh; after restore context fresh without refresh | stale-fixture-mutation.json; fixture-stale-search.json; fixture-context-restored.json |
| C13 | Installed protocol/session/search regressions | PASS: six tests, zero exit codes, empty stderr; includes mismatch/path traversal and no-hooks Garage | installed-regressions-after-restart.json |
| C14 | Preserve installed/config/registered evidence | PASS: no owned mismatch; Workplace config and original capsule/evidence unchanged | final-verification.json |

Actual host calls are captured as MCP content wrappers. reconnect-proof.json is
explicitly a separate connection; it supplements C07–C11, never substitutes for them.
JSON-RPC request IDs are visible for that connection. The host abstraction does not
expose its transport request IDs; none are fabricated in acceptance records.
