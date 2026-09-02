# Real Project Stage Transition Acceptance

Date: 2026-09-02

Target: `wt-image-resize-and-convert-joomla-plugin` (external Joomla project).

## Result

PASS. Run `garage-declarative-process-execution-final-external-acceptance-2026-09-0` completed through the pinned `software-feature-development` Process version `1.1.0`.

## Public API Transcript

1. `pf.context` returned `start_work`.
2. `pf.work.start(objective)` selected `orchestration` with `stage_selection=process_initial_stage`.
3. Repeated `pf.work.state` and `pf.work.transition(completed, evidence, notes)` advanced:
   `orchestration -> intake-scope -> investigation -> domain-modeling -> architecture-plan -> implementation -> code-assurance -> release-delivery -> evolve`.
4. The `evolve` transition returned `run_completed`.

No manual Run/Task lifecycle command was used. `run-doctor` and `events-validate` had passed for the preceding external acceptance; the final acceptance uses the same public API path after the integrity fixes.

## Discovered And Fixed During Acceptance

An artifact marked optional globally but consumed as a later stage input must still be collected at its producing stage. The service now treats any artifact referenced by `required_inputs` as required for the producing stage. The final acceptance passed after that fix.
