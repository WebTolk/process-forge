# Первый собственный процесс

Создавайте process definition через authoring workflow, а не ручным написанием
YAML с нуля. Так ProcessForge сохраняет answers, draft, review и итоговый
process pack.

Внутри подключенного проекта:

```bash
python .pf/runtime/bin/pf.py process-authoring-start --project-root . --id quality-audit --title "Quality Audit" --scope project --kind operational --apply
python .pf/runtime/bin/pf.py process-authoring-review --project-root . --id quality-audit
python .pf/runtime/bin/pf.py process-authoring-apply --project-root . --id quality-audit --apply
python .pf/runtime/bin/pf.py process-doctor --project-root . --process quality-audit
```

Проверьте, что процесс можно использовать в run:

```bash
python .pf/runtime/bin/pf.py run-create --project-root . --id quality-audit-run --title "Quality audit run" --process quality-audit --apply
```
