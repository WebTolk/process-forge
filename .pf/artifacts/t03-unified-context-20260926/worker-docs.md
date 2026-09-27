# T03 documentation handoff

Created the bilingual source-behavior guides:

- `docs/concepts/work-context.md`
- `docs/ru/concepts/work-context.md`

Both describe the additive `execution_contract` v1 block, shared capsule builder, intent/lifecycle separation, path/action/output rules, source and capability readiness limits, standalone identity, legacy preparation restriction, immutable no-overwrite behavior, and the source-versus-installed T06 boundary. They link to the existing execution-contract, capsule, and Work-resource concepts.

Checked claims against `src/processforge_core/work_context.py`, `ProcessExecutionService._write_capsule`, CLI capsule creation/doctor, `prepare_worker_run`, and `existing_capsule_status`. I found no contradiction with the accepted T03 architecture requiring a docs change. Documentation is source-qualified and does not claim installed or real-host acceptance. No tests were run and no other files were changed.
