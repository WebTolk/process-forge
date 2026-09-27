# Рантайм-драйверы

Рантайм-драйвер описывает, как ProcessForge готовит или запускает задачу для
отдельного исполнителя. Это необязательный слой: базовый драйвер `manual`
только создаёт материалы запуска и ждёт, что задачу выполнит человек или
внешняя рабочая среда.

Встроенные драйверы:

- `manual`: готовит состояние запуска и не стартует процесс.
- `generic-shell`: запускает явно указанную программу с аргументами.
- `codex-exec`: запускает исполнителя через Codex CLI с проверенными
  подготовленными входными данными.
- `test-echo-worker`: локальный проверочный исполнитель, который пишет
  ожидаемый отчёт.
- `test-shell-agent`: локальный проверочный shell-агент, который пишет отчёт,
  stdout/stderr, process, heartbeat и exit proof artifacts.

Манифесты драйверов лежат в `templates/runtime-drivers/`, общий реестр - в
`templates/registries/runtime-drivers.yaml`. Проект может добавить локальный
реестр в `.pf/runtime/registries/runtime-drivers.local.yaml`.

Команды из подключённого проекта:

```bash
python .pf/runtime/bin/pf.py runtime-driver list --project-root .
python .pf/runtime/bin/pf.py runtime-driver validate --project-root . --driver manual
python .pf/runtime/bin/pf.py runtime-driver describe --project-root . --driver codex-exec
```

В шаблонах команд разрешены только факты текущего запуска:
`{project_root}`, `{run_id}`, `{task_id}`, `{agent_run_dir}`, `{driver_id}`,
`{capsule_path}`, `{worker_prompt_path}`, `{workspace_access_path}`,
`{expected_report_path}`, `{stdout_path}`, `{stderr_path}`,
`{heartbeat_path}`, `{exit_path}`, `{agent_model}` и
`{agent_reasoning_effort}`. Неизвестный placeholder считается ошибкой
валидации.

ProcessForge всегда добавляет служебные переменные окружения:
`PF_RUN_ID`, `PF_TASK_ID`, `PF_AGENT_RUN_DIR`, `PF_AGENT_EXIT_PATH`,
`PF_AGENT_MODEL`, `PF_AGENT_REASONING_EFFORT`, `PF_PROJECT_ROOT`,
`PF_RUNTIME_DRIVER_ID`, `PF_WORKSPACE_ACCESS_FILE`, `PF_WORKER_RUN_ID` и
`PF_WORKER_TASK_ID`, `PF_WORKER_ATTEMPT`, `PF_PREPARED_INPUT_FILE` и
`PF_PREPARED_INPUT_SHA256`. Shell-драйверы не могут переопределить эти имена.

## Подготовка, выполнение и сбор результата

Подготовка исполнителя требует готового [контракта](work-context.md), явно
объявленного отчёта и права записи по его пути. PF создаёт ограниченные,
неизменяемые [входные данные](prepared-input.md) для одной попытки. Обычная
основная Work без этих объявлений к запуску исполнителя не готова. Манифест
содержит разрешённые ресурсы и проверенные ссылки на источники; он не расширяет
права назначения.

`manual` готовит вход без запуска процесса. `generic-shell` использует
`tools/prepared_executor.py`: проверяет манифест, запускает заданную команду,
записывает heartbeat и результат завершения. `codex-exec` получает тот же
манифест через свою обёртку. Такой исполнитель может работать без MCP;
фактический доступ программы к сети и файлам зависит от ограничений ОС.

Запуск готового исполнителя использует уже подготовленную попытку. Изменение
настроек или заблокированная попытка требуют явной повторной подготовки.
Сбор проверяет принадлежность результатов попытке и сохраняет квитанцию;
повторение и восстановление после гибели процесса не должны дублировать события
завершения. В управляемой Work сбор не меняет стадию основной работы. Основной
агент проверяет результат и передаёт свидетельства в `pf.work.transition`.

## Codex Exec

`codex-exec` - штатный драйвер для запуска shell-агентов через Codex CLI.
Драйвер запускает `tools/codex_exec_worker.py`, который проверяет путь,
контрольную сумму и идентичность подготовленного входа, затем передаёт Codex
фиксированные инструкции и манифест. В этом режиме изменяемые prompt, тело
капсулы и указатель workspace-access повторно не читаются.

Драйвер не выбирает модель сам. Её должен задать оркестратор: через
`agent_model`, параметр `--model` или поле `runtime.model` / `workers[].model` в
плане. Как локальное операторское переопределение допускается `PF_CODEX_MODEL`,
если `PF_AGENT_MODEL` пустой. Если модель не задана ни одним способом,
`codex-exec` завершается ошибкой до запуска Codex.

Уровень мышления задаётся отдельно. Допустимые значения: `minimal`, `low`,
`medium`, `high`. ProcessForge сохраняет выбранное значение как
`agent_reasoning_effort`, передаёт его в `PF_AGENT_REASONING_EFFORT`, а
манифест `codex-exec` перекладывает его в `PF_CODEX_REASONING_EFFORT`. Обёртка
Codex затем добавляет аргумент `-c model_reasoning_effort="<value>"`. Если
значение пустое, этот аргумент не добавляется.

Доступ к общим знаниям, шаблонам, инструментам и MCP рабочего места решается во
время запуска. В публичных assignment и capsule остаются только id ресурсов или
`path_ref`; абсолютные пути остаются в приватных файлах среды выполнения,
включая `workspace-access.json` и манифест попытки. Старый прямой вызов обёртки
может читать workspace-access и передавать `--add-dir`; подготовленный запуск
не выдаёт через этот файл доступ к целым каталогам. Ресурс с разрешением только
на метаданные не даёт права читать его содержимое.

Пример прямого запуска shell-агента с моделью `chatgpt-5.3-codex-spark` и
уровнем `high`:

```bash
python .pf/runtime/bin/pf.py task-create --project-root . --run docs-run --id docs-worker --title "Docs worker" --process task-batch-execution --allowed-file ".pf/artifacts/docs-worker.md" --required-output "id=report,path=.pf/artifacts/docs-worker.md" --expected-report-artifact ".pf/artifacts/docs-worker.md" --workspace-knowledge-resource <knowledge-resource-id> --reasoning-effort high --apply
python .pf/runtime/bin/pf.py worker-run start --project-root . --task docs-worker --driver codex-exec --model chatgpt-5.3-codex-spark --reasoning-effort high
```

Для другого уже объявленного и готового к запуску назначения с той же моделью
можно выбрать уровень `medium`:

```bash
python .pf/runtime/bin/pf.py worker-run start --project-root . --task test-worker --driver codex-exec --model chatgpt-5.3-codex-spark --reasoning-effort medium
```

В оркестраторском плане можно задать общий уровень и переопределить его для
отдельного исполнителя:

```yaml
runtime:
  default_driver: codex-exec
  model: chatgpt-5.3-codex-spark
  reasoning_effort: medium
workers:
  - id: docs-worker
    title: Docs worker
    process: task-batch-execution
    reasoning_effort: high
    workspace_access:
      knowledge_resources:
        - docs.joomla
```

Применение плана:

```bash
python bin/pf.py orchestrator-shell-plan-apply --project-root . --run docs-run --apply
```

`orchestrator-shell-plan-apply --model <model>` может переопределить модель для
всех shell-агентов плана. Уровень мышления сейчас задаётся в YAML-плане, в
сгенерированном assignment или при `worker-run prepare/start` через
`--reasoning-effort`.

Shell-запуск выполняется с `shell=False`. Обычные shell-драйверы по умолчанию
объявляют отсутствие сетевого доступа; `codex-exec` объявляет его для обращения
к провайдеру модели. Эти декларации сами по себе не ограничивают сеть средствами ОС.

ProcessForge не устанавливает агентов, не создаёт агентские папки и не требует
фонового сервиса для работы реестра драйверов.
