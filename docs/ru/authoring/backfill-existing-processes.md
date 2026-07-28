# Backfill existing processes

Backfill создает authoring session из существующего process definition.

```bash
python .pf/runtime/bin/pf.py process-authoring-import --project-root . --process <process-id> --apply
```

Результат сохраняется в:

```text
.pf/authoring/backfill/processes/<process-id>/
  answers.yaml
  draft.process.yaml
  source.process.yaml
  semantic-map.yaml
  unsupported-fields.yaml
  import-report.md
```

`source.process.yaml` фиксирует исходник, `draft.process.yaml` показывает
кандидат, собранный из answers, а `semantic-map.yaml` объясняет сопоставление
полей. Unsupported fields становятся WARN, а не скрытой потерей данных.
