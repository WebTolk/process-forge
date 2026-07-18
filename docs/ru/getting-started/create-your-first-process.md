# Первый собственный процесс

Создавайте process definition через authoring workflow, а не ручным написанием
YAML с нуля. Так ProcessForge сохраняет answers, draft, review и итоговый
process pack.

Внутри подключенного проекта:

```bash
python .pf/runtime/bin/pf.py process-authoring-start --project-root . --id seo-audit --title "SEO Audit" --scope project --kind operational --apply
python .pf/runtime/bin/pf.py process-authoring-review --project-root . --id seo-audit
python .pf/runtime/bin/pf.py process-authoring-apply --project-root . --id seo-audit --apply
python .pf/runtime/bin/pf.py process-doctor --project-root . --process seo-audit
```

Проверьте, что процесс можно использовать в run:

```bash
python .pf/runtime/bin/pf.py run-create --project-root . --id seo-audit-run --title "SEO audit run" --process seo-audit --apply
```
