# Первый собственный процесс

Создавайте process definition через process authoring workflow, а не ручным
написанием YAML с нуля. Так ProcessForge сохраняет ответы, черновик, проверку и
итоговый process pack.

Используйте окружение из [инструкции установки](installation.md). Внутри
подключённого проекта сначала создайте сессию авторинга. Затем заполните её
`answers.yaml`, описав стадии, артефакты и проверки, и только после этого
выполните review и apply:

```bash
python .pf/runtime/bin/pf.py process-authoring-start --project-root . --id quality-audit --title "Quality Audit" --scope project --kind operational --apply
```

Заполните `.pf/authoring/processes/quality-audit/answers.yaml`, затем проверьте
предложение и примените согласованное определение:

```bash
python .pf/runtime/bin/pf.py process-authoring-review --project-root . --process quality-audit
python .pf/runtime/bin/pf.py process-authoring-apply --project-root . --process quality-audit --apply
python .pf/runtime/bin/pf.py process-doctor --project-root . --process quality-audit
```

Приватная сессия хранится в `.pf/authoring/processes/quality-audit/`, а
применённый пакет процесса — в проектных `processes/`, `prompts/`,
`docs/processes/` и `examples/process-authoring/`.

Для обычной работы используйте управляемый Work: см.
[декларативное выполнение](../concepts/declarative-process-execution.md).
Ниже — отдельный пример создания совместимого run:

```bash
python .pf/runtime/bin/pf.py run-create --project-root . --id quality-audit-run --title "Quality audit run" --process quality-audit --apply
```
