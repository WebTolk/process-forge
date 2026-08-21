# cli-integration-audit

## Статус

Планирование выполнено без продуктовых правок. Доступного scope достаточно для реализации чеклиста: нужные точки входа находятся в разрешённых файлах.

## Подтверждённое состояние

- Контракт требует общий `status / initialize / repair`: обязательные поля `status` описаны в `.pf/artifacts/project-init-local-search-mcp-20260821/project-initialization-contract.md:24-41`, `initialize` в строках `43-64`, `repair` в строках `66-85`.
- В Core уже есть минимальный read/apply слой: `src/processforge_core/project_initialization.py:20-35` и явный guard `apply_requested is True` в `src/processforge_core/project_initialization.py:38-43`.
- CLI `init-project`, `project-init`, `project-onboard` сейчас напрямую вызывают `command_init_project` (`tools/processforge.py:24486-24523`), а сама функция содержит writer/doctor поток без shared adapter (`tools/processforge.py:5771-5838`).
- `mcp-register` имеет `--dry-run/--apply` parser-флаги (`tools/processforge.py:24751-24762`), но функция пишет registry при любом не-`dry_run` вызове (`tools/processforge.py:23574-23590`).
- Snapshot producer собирает `resolved.knowledge_resources`, `resolved.available_knowledge_resources`, tools/templates и mcp агрегаты (`tools/processforge.py:9731-9733`, `tools/processforge.py:9837-9848`, `tools/processforge.py:9880-9888`), но не публикует явный `local_search_resources`.
- Search consumer уже ожидает `snapshot.local_search_resources` (`src/processforge_core/local_resource_search.py:74-83`), но индекс сейчас построен вокруг файловых roots и raw path-кандидатов (`src/processforge_core/local_resource_search.py:86-114`, `src/processforge_core/local_resource_search.py:130-141`).
- MCP facade уже read-only и содержит `pf.search` (`tools/pf_runtime/mcp_server.py:15-24`, `tools/pf_runtime/mcp_server.py:77-88`), но `docs/concepts/runtime-mcp.md:7-9` ещё не отражает `pf.search`.

## Реализационный чеклист

1. Расширить `src/processforge_core/project_initialization.py`.
   - Оставить `status()` как read-only adapter, но довести ответ до контракта: `state`, `snapshot`, `snapshot_health`, `workplace`, `resources`, `mcp`, `repair_plan`, `public_safety`.
   - Добавить `initialize(..., execute)` после `status()` и перед `apply()`: функция должна только валидировать контракт и передавать writer callback в `apply("initialize", ...)`.
   - Добавить `repair(..., execute)` после `apply()` или сразу после `initialize()`: repair должен строить/возвращать план в dry-run и выполнять callback только через тот же `apply_requested is True`.
   - Не переносить сюда существующую CLI бизнес-логику из `command_init_project`; Core adapter должен оркестрировать callbacks, а не дублировать создание `.pf`, snapshot refresh или doctor.

2. Подключить Core adapter в CLI.
   - В `tools/processforge.py` добавить import рядом с текущими core imports после `tools/processforge.py:45-59`.
   - В `command_init_project` (`tools/processforge.py:5771-5838`) вынести текущий apply writer-блок строк `5811-5838` во внутренний `execute_initialize()` и вызвать `project_initialization.initialize(..., apply_requested=args.apply, execute=execute_initialize)`.
   - Dry-run строки `5805-5809` оставить read-only, но формировать тот же contract-shaped preview.
   - Добавить `command_project_init_status` рядом с `command_init_project`: вызывает `project_initialization.status(project_root, core_adapter, workplace=args.workplace)` и печатает JSON/текст.
   - Добавить `command_project_init_repair` рядом с `command_init_project`: dry-run показывает repair plan; apply запускает только разрешённые repair callbacks.

3. Закрыть apply guard для прямых function-level вызовов.
   - В `command_mcp_register` изменить условие `if args.dry_run:` на fail/proposal-before-apply: если `args.apply is not True`, писать только proposal и возвращать `0`; registry write строки `23578-23590` выполнять только при `args.apply is True`.
   - Аналогично проверить `command_init_project`: любые записи должны быть внутри callback, прошедшего `project_initialization.apply(...)`.
   - В `main()` strict set (`tools/processforge.py:26093-26111`) можно добавить `mcp-register` только если нужно требовать ровно один флаг; если сохраняется implicit dry-run policy строк `26112-26120`, function-level guard всё равно обязателен.

4. Добавить snapshot search producer metadata.
   - В `build_project_context_snapshot` после формирования `resolved_knowledge_resources` и `available_knowledge_resources` (`tools/processforge.py:9731-9733`) собрать `local_search_resources`.
   - В return dict добавить top-level `local_search_resources` рядом с `resolved` (`tools/processforge.py:9837-9848`) или сразу перед ним.
   - Поля producer entry: `resource_id`, `package_id`, `instance_id`, `kind`, `title`, `tags`, `summary`, `resolved_version`, `resolved_generation`, `fingerprint`, `path_ref`, `producer`, `snapshot_id`.
   - Не класть публично raw absolute paths. Content roots допустимы только если они уже snapshot-authorized/private-runtime safe.

5. Довести search индекс до metadata-first.
   - В `src/processforge_core/local_resource_search.py:74-83` оставить `local_search_resources` как явный producer input.
   - В `build_index` (`src/processforge_core/local_resource_search.py:148-169`) добавить metadata-only документы, чтобы пустой/закрытый content corpus всё равно искал по title/tags/summary/path_ref.
   - Расширить таблицу `documents` (`src/processforge_core/local_resource_search.py:158`) producer/provenance колонками без raw private path.
   - В `search()` result (`src/processforge_core/local_resource_search.py:201`) вернуть producer metadata в `provenance`, но не возвращать resolved local coordinates.

6. Подключить MCP status wiring без write surface.
   - В `tools/pf_runtime/mcp_server.py:15-24` добавить read-only tool, например `pf.project_initialization.status`.
   - В `tool_schema()` (`tools/pf_runtime/mcp_server.py:94-104`) оставить только `session_id` и `project_root`; initialize/repair через MCP не добавлять, потому что facade read-only.
   - В `tool_result()` добавить branch после Ledger binding строк `62-70` и перед `pf.project_state`: определить bound project и вернуть `project_initialization.status(bound_project, core, workplace=str(workplace))`.
   - Документировать `pf.search` и новый status tool в `docs/concepts/runtime-mcp.md:7-17`.

## Регрессии

Рекомендуемые focused checks после реализации:

```bash
python -m pytest tests -k "project_initialization or local_resource_search or mcp_server or project_onboard or mcp_register"
python tools/processforge.py init-project --project-root <tmp-project> --workplace <tmp-workplace> --type generic --dry-run
python tools/processforge.py mcp-register --workplace <tmp-workplace> --id pf-runtime --capability runtime_read --command "python tools/pf_runtime/mcp_server.py --workplace <tmp-workplace>" --dry-run
python tools/processforge.py project-context-refresh --project-root <tmp-project> --dry-run
```

MCP smoke после наличия Ledger session:

```bash
python tools/pf_runtime/mcp_server.py --workplace <workplace> --session <session-id>
```

Проверить JSON-RPC: `initialize`, `tools/list`, `tools/call pf.project_initialization.status`, `tools/call pf.search`, mismatch `session_id`, чужой `project_root`.