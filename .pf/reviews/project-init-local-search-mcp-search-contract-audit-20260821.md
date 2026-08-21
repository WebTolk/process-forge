# Search Contract Audit

## Статус

`PASS_WITH_FINDINGS`

Минимальная безопасная реализация уже частично есть: `pf.search` подключен в MCP, привязан к Ledger-сессии, требует fresh snapshot, не ходит по workplace сам и передает физические корни только во временную runtime-копию snapshot. Основной недобор для целевого сценария: snapshot-authorized template search и детерминированная навигация от результата `pf.search` к локальному файлу Codex пока не закрыты контрактно.

## Подтверждено

- `tools/pf_runtime/mcp_server.py`
  - `pf.search` есть в `TOOLS`.
  - Перед поиском выполняется Ledger binding: session -> project.
  - `project_root` отвергается, если не совпадает с Ledger-bound project.
  - Для `pf.search` требуется `project_context_check_result` со статусом `fresh` или `fresh_with_updates`.
  - Snapshot читается из `project_context_snapshot_paths`.
  - `path_ref` разрешается через `resolve_workspace_path_ref` и добавляется как `content_roots` только в `runtime_snapshot`, без записи в публичный snapshot.

- `src/processforge_core/local_resource_search.py`
  - Поисковый модуль не читает registry/workplace сам.
  - Corpus строится только из records, переданных через snapshot.
  - SQLite FTS5 index хранится в `.pf/runtime/local-resource-search/search.sqlite`.
  - Index rebuild привязан к checksum/id snapshot.
  - Есть лимиты на файл и пагинацию.
  - Нет произвольного root-параметра от MCP-клиента.

- `tools/processforge.py`
  - `build_project_context_snapshot` уже производит `local_search_resources`.
  - `resolve_workspace_path_ref` содержит containment-check для `package` и registry roots.
  - Public snapshot хранит `path_ref`, а не физические absolute paths.
  - `workspace_access_runtime_document` уже показывает рабочий паттерн private runtime grant/resolution для knowledge/templates/tools/mcp.

## Найденные разрывы

1. `local_search_resources` сейчас строится только из `available_knowledge_resources`.

   В `build_project_context_snapshot` producer берет `package_resources`, создает `available_knowledge_resources`, затем мапит их в `local_search_resources`. `resolved.templates` содержит только `{id, status}` и не дает searchable `path_ref`. Поэтому template search в реальном snapshot не гарантирован.

2. Smoke покрывает search core и MCP boundary, но template search пока имитируется вручную.

   `tools/smoke_project_init_local_search_mcp.py` вручную дописывает `snapshot["local_search_resources"]`. Это проверяет потребителя, но не проверяет producer seam: project context refresh должен сам добавить template records.

3. Результат `pf.search` недостаточен для надежной локальной навигации.

   Search result возвращает `canonical_path` и строковый `path_ref` вида `resource_id:canonical`. Это не тот dict-`path_ref`, который принимает `resolve_workspace_path_ref`. MCP `pf.resolve` schema сейчас принимает только `resource_id`; переход `pf.search result -> pf.resolve -> локальный файл` контрактно не доказан.

4. Registry alias для templates неоднозначен.

   `workspace_registry_specs` сейчас мапит `templates` на collection `template_roots`, тогда как `template_create` регистрирует конкретные шаблоны в collection `templates`. Если использовать `{"registry": "templates", "id": "<template-id>"}`, resolver может искать не concrete template, а template root. Без исправления это слабое место для grants и будущего `pf.resolve(path_ref=...)`.

5. Внутренний `host.resolve_payload` не входит в `allowed_read_files`.

   Поэтому точное текущее поведение `pf.resolve` проверить нельзя. Аудит может указать MCP seam, но не может подтвердить весь resolver implementation path без расширения read scope.

## Минимальный безопасный implementation map

### Producer seam

Файл: `tools/processforge.py`

Изменить producer рядом с `build_project_context_snapshot`:

- Вынести построение search records в helper, например `project_local_search_resources(...)`.
- Оставить knowledge records как сейчас.
- Добавить template records из `specialization_context["activated_templates"]` и/или `context_requirements["templates"]`.
- Для concrete template использовать metadata-only record:
  - `id`
  - `resource_id`
  - `kind: template`
  - `package_id` или `template_root`
  - `path_ref`
  - `status`
  - `load_policy: snapshot_authorized`
  - `index_policy: metadata_first` или `full_text` для template directory

Безопасный `path_ref` для template лучше строить через `template_roots` + `relative_path` к директории шаблона, а не через absolute path. Если выбран вариант `registry: templates`, сначала нужно исправить resolver mapping так, чтобы `templates` означал concrete template entries, а `template_roots` остался отдельным root registry.

### Resolver seam

Файлы: `tools/processforge.py`, `tools/pf_runtime/mcp_server.py`

Минимально добавить в `pf.resolve` поддержку одного из вариантов:

- `path_ref` object;
- или `resource_id` + `canonical_path`.

Правило: resolver должен принимать только references, которые есть в текущем fresh snapshot или являются безопасным child-path от snapshot-authorized root. Затем он вызывает существующий `resolve_workspace_path_ref` и возвращает private runtime navigation payload:

```yaml
status: resolved
resource_id: ...
kind: ...
path_ref: ...
canonical_path: ...
local_path: ...
privacy: private_runtime
```

`local_path` допустим в MCP private response, но не должен попадать в public snapshot, assignment capsule, reviews или reports.

### Search core seam

Файл: `src/processforge_core/local_resource_search.py`

Нужны небольшие изменения:

- `AuthorizedRoot` должен хранить исходный root `path_ref` metadata, не только absolute `root`.
- Document row должен хранить `root_path_ref` и `canonical_path`.
- Search result должен возвращать machine-resolvable `file_path_ref` или `root_path_ref + canonical_path`, а не только строку `resource_id:canonical`.

Сам индекс остается rebuildable/private; source of truth остается snapshot.

### MCP seam

Файл: `tools/pf_runtime/mcp_server.py`

- Оставить Ledger binding и fresh snapshot gate как сейчас.
- Не добавлять global/workplace fallback.
- Для `pf.search` не принимать root/path от клиента.
- Для `pf.resolve(path_ref=...)` повторить session/project binding и snapshot membership check.
- Обновить tool descriptions: `pf.search` ищет неизвестный локальный ресурс; `pf.resolve` превращает известный snapshot-authorized ref в canonical private navigation payload.

### Test seam

Файл: `tools/smoke_project_init_local_search_mcp.py`

Добавить проверки:

- Создать/зарегистрировать template через существующий template registry path.
- Сделать project context refresh без ручной правки snapshot.
- Проверить, что snapshot сам содержит `local_search_resources` с `kind: template`.
- Запрос вроде `Joomla plugin manifest` возвращает template result.
- В workspace есть template/resource C вне snapshot; `pf.search` его не видит.
- Из результата `pf.search` вызвать `pf.resolve` и получить существующий локальный файл/директорию.
- Wrong project/session дает `session_project_mismatch`.
- Public snapshot/report не содержит absolute path.
- Existing knowledge search, stale snapshot rebuild, escaped `../outside.md`, ambiguous pagination остаются PASS.

## Рекомендованный порядок

1. Зафиксировать resolver contract: `pf.resolve` принимает `path_ref` или `resource_id + canonical_path`.
2. Исправить template registry mapping или явно использовать `template_roots + relative_path`.
3. Расширить snapshot producer для template records.
4. Расширить search result до resolvable refs.
5. Добавить template/navigation smoke.
6. Запустить existing smoke и targeted regression.

## Итог

Безопасная архитектура уже выбрана правильно: snapshot остается единственным effective context, MCP не пересобирает specialization/process/platform, физические paths появляются только в private runtime. Для завершения целевого контракта нужен не новый поисковый слой, а узкая доработка producer/resolver/test seams: templates должны попадать в `local_search_resources` из snapshot, а результат `pf.search` должен иметь проверяемый путь в `pf.resolve` до локального файла.