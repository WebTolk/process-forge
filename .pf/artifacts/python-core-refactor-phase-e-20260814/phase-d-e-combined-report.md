# Общий отчёт: Phase D и Phase E Python Core refactor

## Статус

Оба прохода завершены и закрыты средствами Process Forge:

- `python-core-refactor-phase-d-20260814` — classification/metadata convergence;
- `python-core-refactor-phase-e-20260814` — public catalog adapter seam.

Для обоих run пройдены `task-doctor`, `run-doctor`, `events-validate` и `git diff --check`.

## Phase D — единый источник classification/metadata

### Цель

Убрать дублирование логики классификации Process Definition между shared Core и legacy validation/reporting, не перенося CLI policy/reporting код в Core.

### Результат

- `processforge_core.process_catalog` публично экспортирует `PROCESS_CATALOG_CLASSIFICATIONS` и `process_catalog_metadata`.
- `tools/processforge.py` импортирует эти сущности через package root.
- В legacy CLI сохранены совместимые имена: константный alias и тонкая обёртка `process_catalog_metadata()`.
- `process_is_public_stable()`, `validate_process_contract()` и `builtin_process_catalog_report()` остались в CLI; их поведение и пользовательские тексты не менялись.

### Проверки

- Компиляция изменённых модулей прошла.
- `python tools/processforge.py --help` и `python bin/pf.py --help` прошли.
- Подтверждены identity shared/legacy константы и parity metadata fallback для draft, active, experimental, internal, deprecated, а также явных classification/public_surface.
- Независимый code review выявил существующий private catalog-helper bridge. Отдельная `gpt-5.4` adjudication подтвердила: это residual adapter debt Phase C, а не дефект или scope-expansion Phase D.

### Итог

Phase D принят как `PASS WITH RESIDUAL RISK`: логика classification/metadata имеет единый источник истины в Core.

## Phase E — публичный catalog adapter seam

### Цель

Закрыть residual adapter debt, оставшийся после Phase D: убрать из CLI прямой импорт `process_catalog.service` и обращения к private helper'ам.

### Результат

В `processforge_core.process_catalog` опубликованы ровно три adapter API:

- `official_process_definition_refs(context, *, include_available=False)`;
- `process_root_candidates(context)`;
- `process_root_yaml_files(root, *, legacy_flat)`.

Их реализации — тонкие делегаты уже существующих private helper'ов. В `tools/processforge.py` сохранены прежние CLI wrapper signatures и построение `ProcessCatalogContext`, но вызовы переведены на package-root imports. Прямой импорт `process_catalog.service` удалён.

### Сохранённые инварианты

- порядок roots: flow user/custom → project user/custom → distribution user/custom → project core → distribution core → legacy flat;
- official entries вставляются перед первым `core` root;
- duplicate policy остаётся `first wins`, strict добавляет warning;
- active official pack gating и `include_available` не изменены;
- `legacy_flat=True` ограничивает YAML walk верхним уровнем, иначе используется рекурсивный обход;
- Core не получил обратную зависимость на CLI и не импортирует package root из `service.py`.

### Проверки качества

- Независимый `gpt-5.4` design review: PASS с ограничением не раскрывать дополнительные internals.
- Независимый `gpt-5.4` code review: PASS, private service imports/calls из CLI не найдены.
- `gpt-5.3-codex-spark` выполнил inventory и characterization. В первичном отчёте identity-секция перечислила прежние API, поэтому она была частично отклонена.
- Выполнен отдельный Spark identity retry; его static seam evidence дополнено прямой оркестраторской runtime-проверкой `is` для всех трёх новых CLI aliases и public exports — все три дали `True`.

## Воркеры и контроль

Простые инвентаризации, characterization и corrective retry поручались `gpt-5.3-codex-spark`. Архитектурный дизайн, независимые reviews, patch design и adjudication поручались `gpt-5.4`.

Воркеры не вносили product edits: их ограничения позволяли создавать только собственные Process Forge артефакты. Reviewed product diffs применялись основным оркестратором через `apply_patch`, затем независимо проверялись.

## Общий итог

После Phase D и E:

- classification/metadata более не дублируется между Core и legacy CLI;
- legacy CLI больше не зависит напрямую от internal `process_catalog.service` API;
- необходимый catalog adapter surface явным образом опубликован через package root;
- граница Core/CLI стала чище без переноса runtime, MCP, hooks, event/state, authoring или reporting policy в Core.

## Остаточные ограничения

- Рабочее дерево содержит накопленные незакоммиченные изменения и Process Forge артефакты; коммит в этих проходах не создавался.
- Git выдаёт информативные предупреждения о потенциальной LF→CRLF нормализации ряда adapter-файлов, но `git diff --check` проходит.
- Не запускался полный release-test: валидация была намеренно сфокусирована на затронутом Core/CLI seam и на независимых review.
