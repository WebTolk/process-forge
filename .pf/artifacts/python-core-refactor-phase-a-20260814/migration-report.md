# Отчёт о миграционном влиянии Python Core Refactor

## Итог

Для выбранной архитектуры Phase A целевой вариант уже зафиксирован как **`process-centric modular core + thin adapters`** с первым выносом **Process Definition slice**, а не Runtime-first split и не utility-bucket extraction (`.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-target-architecture.md`, `.pf/artifacts/python-core-refactor-phase-a-20260814/independent-architecture-review.md`).

Из этого следует базовое правило миграции:

- **Сначала** выносится повторно используемая process-definition логика в Core API.
- **CLI, Runtime, MCP и hooks** должны перейти на этот Core API как thin adapters.
- **Совместимость** должна жить на adapter boundary или в явном compatibility-normalization слое, а не становиться новой внутренней нормой Core.
- **Семантика event/projection/work-state** не должна остаться неявно привязанной к `tools/pf_runtime/host.py`; это отдельный следующий slice, а не часть process-definition extraction.

## 1. Что считается behavior-preserving extraction

Ниже перечислены изменения, которые по имеющимся артефактам считаются допустимым выносом без обязательной миграции пользовательских данных и без целенаправленного breaking surface.

### 1.1. Вынос process-definition логики в Core

Под вынос уже явно подпадают:

- загрузка process definition;
- authoring normalization;
- materialization из authoring answers;
- contract validation;
- process doctor;
- route/handoff contract checks, если они относятся к process-definition, а не к runtime transport.

Это прямо совпадает с рекомендуемым первым slice в target architecture (`python-core-target-architecture.md`).

### 1.2. Сохранение thin launcher boundary

`bin/pf.py` уже реализован как минимальный launcher, который только находит `tools/processforge.py` и передаёт управление дальше (`bin/pf.py`).

Если после рефакторинга:

- `bin/pf.py` остаётся публичным entrypoint;
- `tools/processforge.py` остаётся executable adapter target;
- команды и их аргументы не меняются,

то это **behavior-preserving extraction**.

### 1.3. Переключение Runtime/MCP/hooks с прямого monolith import на package imports

Архитектурный обзор прямо требует убрать зависимость от `sys.path.insert(...)` и `importlib.import_module("processforge")` в `tools/pf_runtime/codex_hooks.py` и `tools/pf_runtime/mcp_server.py`, заменив её на imports Core package (`python-core-target-architecture.md`, `independent-architecture-review.md`).

Если при этом сохраняется текущая observable semantics read-only surfaces:

- `pf.project_state`
- `pf.work_state`
- `pf.resolve`
- `pf.workplace_state`

то это migration-free internal extraction, а не breaking change (`docs/concepts/runtime-model.md`).

## 2. Что требует compatibility obligations

Ниже перечислены поверхности, для которых репозиторий уже подтверждает действующие compatibility obligations.

### 2.1. CLI имена команд

Публичные документы уже закрепляют канонические имена и отдельно помечают compatibility-only aliases.

Обязательства:

- `project-onboard` остаётся каноническим именем, `init-project` остаётся compatibility name (`docs/concepts/project-init.md`, `README.md`).
- `workplace-init` остаётся публичным именем, `init-workplace --root` остаётся lower-level compatibility name (`docs/concepts/workplace-init.md`).
- `project-context-refresh`, `project-context-check`, `assignment-capsule` являются новым flow; `context-resolve` и `context-compile` уже помечены как compatibility-only (`tools/README.md`).
- `execution-inspector-*` уже документированы как clearer aliases, а `supervisor*` как historical technical CLI names; значит, их нельзя убрать без объявленного migration/breaking шага (`docs/concepts/director-ledger-inspector-boundary.md`, `README.md`, `docs/concepts/process-supervisor.md`).

### 2.2. Process-definition vocabulary

Документация уже фиксирует:

- использовать `exit_gates`, а не legacy alias `gates`;
- использовать `automation_bindings`, а не прежнее `technical_obligations`, которое “remains readable only for compatibility” (`docs/authoring/process-authoring.md`).

Следовательно:

- чтение `gates` и `technical_obligations` сейчас является подтверждённой compatibility obligation;
- запись новых public artifacts в старой форме не требуется и противоречит документированной canonical surface.

### 2.3. Runtime inspector surface

`supervisor` и `execution-inspector-*` описаны как совместимые имена одной роли, а не как независимые подсистемы. Значит, refactor не должен развести их поведение или оставить только один набор имён без явного migration note (`docs/concepts/director-ledger-inspector-boundary.md`, `docs/concepts/process-supervisor.md`).

## 3. Что можно чистить без обязательной миграции

По Phase A уже выделены слабые или transitional compatibility surfaces, которые можно вычищать после проверки usage и обновления docs/examples.

### 3.1. Weak aliases

Слабые кандидаты на cleanup:

- `smoke-all` как alias для `release-test`;
- `builtin-process-catalog-doctor --project-root` как alias к `--root`;
- `gates` как legacy alias.

Это подтверждено в `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-compatibility-cleanup.md`.

### 3.2. Transitional command names

Переходные имена, которые пока ещё нужно читать, но не продвигать как canonical:

- `context-resolve`
- `context-compile`
- `init-project`
- `technical_obligations`
- legacy flat process layout

Их допустимо сохранить как временный compatibility layer, но Phase A уже предполагает, что они не должны определять форму Core API.

## 4. Что является intentional breaking change, а не просто extraction

Ниже случаи, которые нельзя маскировать под “внутренний рефакторинг”.

### 4.1. Удаление документированных compatibility aliases без transition window

Breaking change будет, если без отдельного migration notice убрать:

- `init-project`
- `init-workplace`
- `context-resolve`
- `context-compile`
- `supervisor*`
- чтение `technical_obligations`
- чтение `gates`

Потому что их наличие подтверждено текущими docs/CLI/artifacts.

### 4.2. Перевод compatibility semantics внутрь Core как новой канонической модели

Independent review отдельно предупреждает, что deprecated alias/fallback не должен стать новой нормой Core. Если Core будет проектироваться вокруг legacy surface, это уже не preservation, а архитектурный drift (`independent-architecture-review.md`).

### 4.3. Изменение release/public surface

Breaking change будет, если refactor изменит публичный способ запуска или состав release без синхронного изменения release contract:

- канонический public launcher `python bin/pf.py`;
- публичное наличие `tools/processforge.py` как delegate target;
- release roots and required files from `RELEASE_DIRS`, `RELEASE_ROOT_FILES`, `RELEASE_PF_PUBLIC_FILES`, `RELEASE_REQUIRED_PATHS`;
- exclusion policy из `.processforge-releaseignore`.

Это уже часть текущего release contract (`tools/processforge.py`, `.processforge-releaseignore`, `docs/concepts/workplace-vs-project.md`, `docs/concepts/runtime-model.md`).

## 5. Обязательные transition aliases и переходная политика

На основании публичного inventory и compatibility-cleanup артефакта переходная политика должна быть такой.

### 5.1. Сохранить как transition aliases на Phase B/C

Сохранять нужно:

- `init-project` -> `project-onboard`
- `init-workplace` -> `workplace-init`
- `context-resolve` / `context-compile` -> новый context flow
- `technical_obligations` -> canonical `automation_bindings`
- `supervisor*` alongside `execution-inspector-*`

### 5.2. Разрешить удаление только после явной чистки usage

Удалять можно только после проверки и обновления:

- docs
- README / tools README
- examples
- prompts
- process templates
- runtime hooks / MCP / CLI help

Это особенно критично для `handoff_required`, `supervisor*`, `session-*`/`agent-*` related naming and legacy flat process layout, которые в артефакте Phase A помечены как cleanup with migration attention, а не как “можно тихо удалить”.

## 6. Последствия для packaging и release archive

### 6.1. Публичный архив уже зависит от текущих путей

Release surface сегодня явно включает:

- каталоги `docs`, `schemas`, `processes`, `packages`, `packs`, `templates`, `prompts`, `examples`, `policies`, `seeds`, `bin`, `tools`, `updates`, `checksums`;
- root files `README.md`, `README.ru.md`, `QUICKSTART.md`, `QUICKSTART.ru.md`, `CHANGELOG.md`, `LICENSE`, `NOTICE`, `VERSION`, `requirements.txt`, `.gitignore`, `.processforge-releaseignore`;
- public `.pf` files `.pf/AGENTS.md`, `.pf/process-forge.yaml`, `.pf/hooks.yaml`.

Это не предположение, а текущий release contract в `tools/processforge.py`.

### 6.2. Следствие для Python Core extraction

Если появляется новый package root для Core, то нужно обеспечить одно из двух:

- либо он входит в release source и release checks как новый required/public path;
- либо старые публичные launchers и imports продолжают работать без изменения release manifest.

Иначе refactor нарушит `release-pack`, `release-test`, `release-archive-test` contract не архитектурно, а дистрибутивно.

### 6.3. Что не должно попасть в release

`.processforge-releaseignore` уже исключает runtime/artifacts/reviews/handoffs/runs/contexts/assignments/dogfooding/private-notes/cache и служебные каталоги. Значит, миграция Core не должна переносить временные compatibility artifacts в публичный release-архив.

## 7. Явные случаи, где миграция не требуется

Ниже случаи, для которых по имеющимся доказательствам **не нужен отдельный пользовательский migration step**, если сохраняется observable surface.

- Перенос внутренней process-definition логики из `tools/processforge.py` в Core package при сохранении тех же CLI команд и тех же входных/выходных файлов.
- Сохранение `bin/pf.py` как публичного launcher при внутреннем изменении delegate target implementation.
- Замена прямых monolith imports в Runtime/MCP/hooks на package imports при сохранении тех же read-only capabilities.
- Внутреннее разделение `tools/processforge.py` на thin adapter + Core API, если docs/examples/public commands не меняются.
- Перенос helper-функций в ограниченный `common/*` слой, если он не превращается в новый dumping ground и не меняет public contract.

## 8. Явные случаи, где нужна миграционная заметка или отдельное решение

- Удаление или скрытие documented aliases без transition window.
- Изменение process-definition field vocabulary так, чтобы старые process files перестали читаться.
- Изменение canonical public launcher.
- Изменение release archive состава без обновления release contract.
- Перенос runtime event/work-state semantics так, что `pf.project_state`, `pf.work_state`, `pf.resolve`, `pf.workplace_state` меняют смысл или структуру.
- Тихое исключение legacy flat process layout без brownfield migration path.

## Заключение

Подтверждённый безопасный путь для Phase A/B/C такой:

1. Вынести **Process Definition slice** в Core.
2. Оставить `bin/pf.py`, `tools/processforge.py`, Runtime, MCP и hooks thin adapters.
3. Держать compatibility aliases вне канонической модели Core.
4. Не менять release/public surface молча.
5. Считать cleanup отдельной работой, а не автоматически “входящей” в extraction.

Итоговая граница проста: **behavior-preserving extraction допустим, если внешний CLI/process-definition/release contract остаётся прежним; cleanup и удаление alias считаются отдельным миграционным решением, а не побочным эффектом выноса Python Core**.