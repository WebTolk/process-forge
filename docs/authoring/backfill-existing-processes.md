# Backfill Existing Processes

Backfill reconstructs authoring metadata for process definitions that already
exist. It does not change the source process.

```bash
python .pf/runtime/bin/pf.py process-authoring-import --project-root . --process task-batch-execution --apply
```

The command writes:

- `.pf/authoring/backfill/processes/<process-id>/answers.yaml`
- `.pf/authoring/backfill/processes/<process-id>/draft.process.yaml`
- `.pf/authoring/backfill/processes/<process-id>/source.process.yaml`
- `.pf/authoring/backfill/processes/<process-id>/semantic-map.yaml`
- `.pf/authoring/backfill/processes/<process-id>/unsupported-fields.yaml`
- `.pf/authoring/backfill/processes/<process-id>/import-report.md`

Unsupported fields are not automatically failures. They mean the current
authoring answers model does not have a direct field for that source data. Review
them before release and decide whether to add authoring coverage, keep a warning,
or narrow the process source.

Run a parity check after import:

```bash
python .pf/runtime/bin/pf.py process-parity-check --project-root . --process task-batch-execution
```

Reports are written under `.pf/reviews/parity/` and `.pf/artifacts/parity/`.
