# Release-Focused Architecture Review: ProcessForge 1.1.0

## Scope

Review of the release-critical changes currently present in the working tree: project process selection, pinned Work capsules, transition rejection/recovery, handoff continuation, MCP bindings, schemas, and release-pack provenance enforcement.

## Findings

| Area | Result | Evidence |
| --- | --- | --- |
| Garage dependency on Runtime/Ledger/hooks | PASS | `smoke_garage_no_hooks_sessionless` and `smoke_garage_work_start_sessionless` passed in the complete source suite. |
| Process selection authority | PASS | The project selection map is normalized once; multiple allowed processes return `process_choice_required`, while a pinned Work stores one selected definition. `smoke_multi_process_work_capsule` passed. |
| Durable rejection recovery | PASS | Invalid transition evidence returns `transition_rejected` before mutation. `smoke_work_transition_recovers_after_invalid_evidence` passed. |
| Completion and handoff | PASS | `smoke_work_transition_final_stage_completes_run` and `smoke_process_transition_handoff` passed. |
| Fresh continuation | PASS | The continuation lookup selects the newest completed boundary and does not re-offer a consumed older handoff; this is covered by `smoke_multi_process_work_capsule`. |
| Resource narrowing/search | PASS | `smoke_garage_real_joomla_search` and cross-project isolation smoke passed. |
| Updater preservation | NOT RUN | Requires an eligible archive and a clean release commit; blocked before archive qualification. |

## Release risk

No architecture blocker was found in the reviewed current change set. The release remains blocked by provenance: a final archive must be built from a clean, explicitly recorded release commit.
