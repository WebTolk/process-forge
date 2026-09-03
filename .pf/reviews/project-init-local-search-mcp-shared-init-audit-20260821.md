# Shared Init Audit

## Статус

Аудит выполнен в read-only режиме. Продуктовый код не изменялся.

## Проверенные источники

- `src/processforge_core/project_initialization.py`
- `tools/processforge.py`
- `tools/pf_runtime/mcp_server.py`
- `tools/pf_runtime/host.py`
- `docs/authoring/project-initialization.md`

## Текущее состояние

1. Core уже содержит общий read model и apply guard:
   - `project_initialization.status(...)` читает состояние `.pf`, snapshot health, workplace и ресурсы: `src/processforge_core/project_initialization.py:20-50`.
   - `initialize(...)` и `repair(...)` пока являются только тонкой оберткой над `apply(...)`: `src/processforge_core/project_initialization.py:53-66`.
   - Эти apply-обертки сейчас не используются CLI/MCP для фактической инициализации или ремонта.

2. CLI project init все еще монолитный и пишет напрямую:
   - `command_init_project(...)` сам нормализует `project_root`, `workplace`, answers, `project_type`, `coordination_mode`: `tools/processforge.py:5772-5787`.
   - Там же выполняется проверка missing workplace, создание greenfield root, dry-run, создание `.pf` директорий, запись файлов, `.gitignore`, snapshot refresh, doctor и события: `tools/processforge.py:5788-5839`.
   - Неразрушающие brownfield-гарантии живут в `write_file(...)` и `append_gitignore_entries(...)`: `tools/processforge.py:1442-1473`.

3. Repair фактически существует отдельно как context refresh:
   - Core status предлагает только `refresh_context` для `partial/stale/broken`: `src/processforge_core/project_initialization.py:50`.
   - Реальная запись snapshot выполняется через `write_project_context_snapshot_outputs(...)`: `tools/processforge.py:10187-10223`.
   - CLI `project-context-refresh` сам делает dry-run proposal или пишет snapshot/telemetry/events: `tools/processforge.py:11382-11454`.

4. MCP сейчас не имеет initialization/repair apply-инструмента:
   - В MCP tools есть только `pf.project_initialization.status`: `tools/pf_runtime/mcp_server.py:16-26`.
   - Статус делегируется в Core после Ledger/session binding: `tools/pf_runtime/mcp_server.py:64-78`.
   - MCP JSON-RPC `initialize` на `tools/pf_runtime/mcp_server.py:136-137` является handshake протокола MCP, не project initialization. Его нельзя смешивать с продуктовой инициализацией.

5. Runtime host init не является project init:
   - `runtime-host init` делегирует в `pf_runtime.host.command_init`: `tools/processforge.py:18476-18479`.
   - `host.command_init(...)` только регистрирует уже onboarded projects в runtime state: `tools/pf_runtime/host.py:547-556`.
   - `route_project(...)` требует существующий `.pf` и `process-forge.yaml`: `tools/pf_runtime/host.py:384-397`.

## Минимальный refactor

1. Расширить `src/processforge_core/project_initialization.py` до application service, а не только apply guard.

   Минимальный API:
   - `status(project_root, core, workplace=None)` оставить совместимым.
   - `initialize_project(request, adapters) -> dict`
   - `repair_project(request, adapters) -> dict`

   `request` должен содержать:
   - `project_root`
   - `workplace`
   - `answers`
   - `project_type`
   - `coordination_mode`
   - `dry_run`
   - `apply_requested`
   - `force`
   - `allow_missing_workplace`
   - `source`: `cli` или `mcp`

2. Перенести в service общую resolver/policy-логику из `command_init_project(...)`:
   - нормализация `project_root`;
   - нормализация `workplace` root -> `workplace.yaml`;
   - merge `--type` в `answers["project"]["type"]`;
   - merge `--coordination-mode` в `answers["coordination"]["mode"]`;
   - правило: dry-run требует существующий project root;
   - правило: apply может создать missing greenfield root;
   - правило: missing workplace запрещен без `allow_missing_workplace`.

3. Не переносить весь `tools/processforge.py` в Core сразу. Чтобы refactor был минимальным, service может принимать adapter callbacks на существующие функции:
   - `load_answers`
   - `build_project_files`
   - `project_mode`
   - `write_file`
   - `append_gitignore_entries`
   - `write_project_context_snapshot_outputs`
   - `run_doctor_project`
   - `finalize_project_onboarding_doctor_artifacts`
   - `emit_process_event`

   Так CLI и MCP будут использовать один сценарий, но без массового перемещения генераторов файлов.

4. Сделать `command_init_project(...)` тонким адаптером:
   - собрать request из argparse;
   - вызвать `project_initialization.initialize_project(...)`;
   - напечатать plan/results;
   - не держать локальную копию resolver/write orchestration.

5. Подключить repair к тому же service:
   - первый поддерживаемый repair action: `refresh_context`;
   - использовать существующий `write_project_context_snapshot_outputs(...)`;
   - dry-run должен возвращать proposal и не писать;
   - apply должен требовать `apply_requested is True`;
   - repair не должен выполнять project onboarding для missing `.pf`.

6. Для MCP добавить только контролируемое исключение, если оно действительно требуется:
   - добавить tools вроде `pf.project_initialization.initialize` и `pf.project_initialization.repair`;
   - оба должны вызывать тот же Core service;
   - destructive path разрешать только при JSON boolean `apply: true`;
   - при отсутствии apply возвращать `ProjectInitializationError("apply_required")`;
   - session-bound project mismatch проверять до записи;
   - не возвращать приватные absolute paths в MCP response;
   - MCP protocol `initialize` оставить только handshake.

7. `tools/pf_runtime/host.py` не нужно вести через project init service.
   Его `command_init(...)` регистрирует runtime handles для уже инициализированных проектов. Максимум допустим узкий reuse resolver-helper, но не смешивание с project onboarding writer.

## Риски, которые refactor должен закрыть

- Сейчас apply guard в Core не защищает CLI writes, потому что CLI его не вызывает.
- CLI и будущий MCP apply могут разойтись в правилах `workplace`, `allow_missing_workplace`, `force`, dry-run/apply.
- Repair объявлен в Core API, но фактически не связан с существующим `project-context-refresh`.
- Runtime host init можно ошибочно принять за project initialization; это отдельная bounded runtime-state операция.

## Рекомендуемые проверки после реализации

- CLI `project-onboard --dry-run`: не создает файлов.
- CLI `project-onboard --apply`: создает greenfield project root и `.pf`.
- Brownfield без `--force`: существующие отличающиеся файлы уходят в `.candidate`.
- `project-context-refresh --dry-run`: не пишет snapshot.
- `project-context-refresh --apply` или default write path: использует `repair_project(..., action=refresh_context)`.
- MCP init/repair без `apply: true`: возвращает `apply_required`.
- MCP init/repair с `apply: true`: проходит через тот же service, что CLI.
- `pf.project_initialization.status` остается read-only и совместимым.