# Рантайм-драйверы

Рантайм-драйвер описывает, как ProcessForge готовит или запускает задачу для
отдельного исполнителя. Это необязательный слой: базовый драйвер `manual`
только создаёт материалы запуска и ждёт, что задачу выполнит человек или
внешняя рабочая среда.

Встроенные драйверы:

- `manual`: готовит состояние запуска и не стартует процесс.
- `generic-shell`: запускает явно указанную программу с аргументами.
- `codex-exec`: запускает shell-агента через Codex CLI, передавая капсулу
  назначения, рабочий prompt и приватный файл доступа к ресурсам рабочего места.
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
`PF_WORKER_TASK_ID`. Shell-драйверы не могут переопределить эти имена.

## Codex Exec

`codex-exec` - штатный драйвер для запуска shell-агентов через Codex CLI.
ProcessForge создаёт капсулу назначения, prompt исполнителя, путь ожидаемого
отчёта, heartbeat-файл и приватный `workspace-access.json`, а затем запускает
`tools/codex_exec_worker.py`.

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
`path_ref`; приватные абсолютные пути пишутся в
`.pf/runtime/agent-runs/.../workspace-access.json`. `codex-exec` читает этот
файл и передаёт найденные директории в Codex через `--add-dir`.

Пример прямого запуска shell-агента с моделью `chatgpt-5.3-codex-spark` и
уровнем `high`:

```bash
python .pf/runtime/bin/pf.py task-create --project-root . --run docs-run --id docs-worker --title "Docs worker" --process task-batch-execution --allowed-file ".pf/artifacts/**" --workspace-knowledge-resource <knowledge-resource-id> --reasoning-effort high --apply
python .pf/runtime/bin/pf.py worker-run start --project-root . --task docs-worker --driver codex-exec --model chatgpt-5.3-codex-spark --reasoning-effort high
```

Второй shell-агент с той же моделью и уровнем `medium`:

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

Shell-запуск выполняется с `shell=False`. Обычные shell-драйверы не получают
сеть по умолчанию; `codex-exec` явно объявляет сетевой доступ, потому что Codex
CLI обращается к своему провайдеру модели.

ProcessForge не устанавливает агентов, не создаёт агентские папки и не требует
фонового сервиса для работы реестра драйверов.
