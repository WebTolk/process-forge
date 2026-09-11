# Source-suite follow-ups

Primary owner, 2026-09-11. These test-only changes followed concrete failures
in the broad source suite; no additional product behavior was changed.

| Check | Observed failure | Repair and proof |
| --- | --- | --- |
| smoke_single_agent_session_flow | Hardcoded old presence filename after exact-session storage repair. | Check one persisted exact session and one checked-out presence record. Current PASS. |
| smoke_project_init_local_search_mcp | Unknown answers_path argument now correctly returns JSON-RPC -32602 before tool dispatch; old assertion expected a tool error result. | Assert protocol code and absent result, preserving the existing valid search/repair tests. Current PASS. |
| smoke_governed_work_stage_resolution | Unknown preferred_stage argument likewise fails at the protocol boundary; helper assumed every response contained result. | Helper retains the actual error envelope in its assertion; test checks exact -32602. Existing helper's own smoke and this check both PASS. |
| smoke_garage_session_enhanced | Snapshot-only resource never reaches Workplace search corpus. The same IndexError reproduced on original HEAD. | Use existing register_fixture_resource/select_fixture_resource helpers and require exactly one expected result both with and without a session. Current PASS. |

Files changed: the four named checks and
`tools/smoke_garage_mode_not_promoted_by_session.py` (shared response helper).
The single-agent update was already recorded before result fixation. The other
four files are an assurance supplement to the immutable stage result.

Evidence: `source-full-report-attempt1.json`, `source-full-remainder.txt`,
`validation/baseline/smoke_garage_session_enhanced.{json,txt}` and corresponding
current records. Failures remain preserved; final aggregate acceptance replaces
only a check's verdict when an actual successful rerun exists. Full source
coverage is not inferred from these focused repetitions alone.
