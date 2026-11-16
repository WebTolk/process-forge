# Проверка перед выпуском

[English version](../release-checklist.md)

Перед публикацией релиза ProcessForge выполните следующие проверки.

Подготовьте чистый кандидат исходников с корневыми `AGENTS.md`, `CONTRIBUTING.md`
и `CONTRIBUTING.ru.md`. Это инструкции для участников разработки. Корневая
`.pf/` репозитория содержит приватное локальное состояние: свежий клон и проверки
дистрибутива должны работать без неё, а её файлы не должны попадать в публичный
инвентарь или ZIP релиза. Локальный `.pf/AGENTS.md` не является обязательным входом
релиза и не заменяет корневые правила для участников разработки.

Стартовый контракт потребительского проекта поставляется отдельно:
`templates/agent-entry-contract.md`, метаданные
`templates/agent-entry-contract.json` и проверенная расширенная проекция
`templates/project-agents-template.md`. Проверки релиза проверяют целостность
этих шаблонов; совпадение инструкций участников разработки и потребительского
проекта не требуется. Прежде чем переносить новый контракт в существующий
потребительский проект, рассмотрите соответствующую миграцию. `release-pack`
не инициализирует исходный проект, не генерирует инструкции и не переписывает
корневые правила для участников разработки.

Запишите точные commit/tree кандидата, включённые изменения и результаты
применимых проверок. После подготовки окончательного состава поставки выполните
`python tools/validate-process-forge-checksums.py --root . --write`, просмотрите
полный diff инвентаря и повторите его проверку. Последующее изменение исходников
требует применимых повторных проверок новой ревизии. Предрелизная версия в
исходниках сама по себе не подтверждает публикацию релиза у провайдера.

```bash
python -m py_compile tools/processforge.py
python tools/validate-process-forge-schemas.py --root .
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-check --root .
python tools/smoke_first_run.py
python tools/smoke_runtime_driver_registry.py
python tools/smoke_worker_run_shell.py
python tools/smoke_process_supervisor_tick.py
python tools/smoke_director_inspector_boundary.py
python tools/smoke_agent_ledger.py
python tools/smoke_single_agent_session_flow.py
python tools/smoke_multi_project_agent_sessions.py
python tools/smoke_multi_agent_as_composed_sessions.py
python tools/smoke_project_coordination_modes.py
python tools/smoke_mixed_workplace_projects.py
python tools/smoke_worker_awareness_of_director.py
python tools/smoke_error_workflow.py
python tools/smoke_process_run_task_batch.py
python bin/pf.py release-test --root . --public --fail-fast
python bin/pf.py dev-test --root . --suite supervisor-stress
python bin/pf.py release-pack --root . --output .pf/tmp/release-check/processforge.zip
python bin/pf.py release-archive-test --archive .pf/tmp/release-check/processforge.zip --root . --extracted-test full
git diff --check
```

В поставку не должны попадать:

- вся корневая `.pf/` репозитория исходников;
- `runtime/`;
- `__pycache__/`;
- временные каталоги smoke-проверок;
- приватные абсолютные пути;
- локальные секреты пользователя;
- payload очередей отправки hooks;
- локальные расшифровки переписки;
- устаревшие архивы `dist/processforge-v*.zip` и соответствующие им манифесты.

Для временных файлов репозитория используйте собственный каталог под `.pf/tmp/`.
В доказательствах квалификации сохраняйте фактические commit исходников, версию
и SHA-256 итогового архива. Повторная сборка требует собственного хэша и
применимых проверок. Порядок публикации и сверки одинаковых артефактов на зеркалах
описан в [руководстве по публикации](../maintainers/release-publishing.md).
