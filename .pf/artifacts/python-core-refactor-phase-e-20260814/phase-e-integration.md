# Phase E integration — public catalog adapter seam

## Delivered

Phase E closes the residual catalog/resolve adapter debt from Phase D.

- `processforge_core.process_catalog` publicly exposes exactly three adapter APIs: `official_process_definition_refs`, `process_root_candidates` and `process_root_yaml_files`.
- Their implementations are minimal delegates over the existing private service helpers; catalog ordering, official-pack gating, duplicate handling and YAML traversal are unchanged.
- `tools/processforge.py` retains its compatible wrappers and context construction, but consumes those functions through the package root.
- The direct `process_catalog.service` import and CLI private-helper calls are removed.

## Assurance

- `gpt-5.3-codex-spark`: inventory, initial characterization and a corrective adapter identity retry.
- `gpt-5.4`: design, independent design review, patch design and independent applied-code review; no Fail findings.
- The first Spark characterization listed the wrong three functions in one identity subsection. It was not accepted as evidence; the corrective task and orchestrator runtime identity checks cover the actual Phase E APIs.

## Deferred

No additional service internals were exposed. Future Core API work must separately justify any public surface beyond these three adapter functions.
