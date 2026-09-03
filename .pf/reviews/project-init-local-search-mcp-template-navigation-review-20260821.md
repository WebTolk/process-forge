# Template Navigation Review

## Итог

Статус: `changes_requested`.

Кодовая схема в целом движется в правильную сторону: snapshot producer пишет для template search только metadata/path_ref, MCP делает Ledger-bound fresh-snapshot check, а `local_path` добавляется только в runtime-ответ. Но в ревью найдены два контрактных риска по registry aliasing/scope containment и один пробел fixture-качества.

## Findings

### 1. Registry path_ref может указывать за пределы workplace/root

Severity: `high`

`resolve_workspace_path_ref()` для registry-based refs берёт `entry["path"]`, прогоняет его через `workplace_path_resolution()`, но дальше проверяет containment только относительно уже разрешённого `base`, а не относительно workplace root или допустимого registry root.

Затронутые места:

- `tools/processforge.py:9231-9243`
- `tools/processforge.py:1238-1267`
- `tools/pf_runtime/mcp_server.py:119-125`
- `tools/pf_runtime/mcp_server.py:128-144`

Следствие: если в `registries/templates.yaml` появится concrete `templates` entry с absolute path или `../...`, `pf.search` примет этот путь как authorized root, проиндексирует файл и вернёт private `local_path`. Это противоречит заявленному “path-ref containment” в `docs/concepts/runtime-mcp.md:28-32`.

Fixture сейчас проверяет escape только через `{"package": "self", "relative_path": "../outside.md"}` (`tools/smoke_project_init_local_search_mcp.py:67-70`, `93-94`), но не проверяет escape через registry entry path. Нужно добавить containment для registry entry path и отдельный smoke на escaped/absolute template registry path.

### 2. У `templates` registry остались два несовместимых смысла

Severity: `medium`

Новая логика разрешает concrete template entries через `workspace_registry_specs()`:

- `tools/processforge.py:9168-9177`
- `tools/processforge.py:9805-9818`

Но `resource_path_ref_missing()` всё ещё считает `registry: templates` ссылкой на `template_roots`, а не на concrete `templates`:

- `tools/processforge.py:9150-9164`

Это создаёт alias regression: snapshot producer пишет `{"registry": "templates", "id": template_id}`, MCP resolver это понимает как concrete template, но path_ref validator/doctor path остаётся на старой модели `template_roots`. В результате часть проверок может ложно отклонять корректные concrete template refs или скрывать несовместимость контрактов.

Нужно привести validator к той же модели, что и `workspace_registry_specs()`, либо явно разделить `template_roots` и `templates` в публичном контракте.

### 3. Fixture недостаточно доказывает отсутствие public path leakage

Severity: `low`

Положительное покрытие есть: fixture проверяет, что template record появился в snapshot, что exact workplace path не попал в snapshot, что MCP template result имеет existing `local_path`, и что public onboarding report не содержит project path.

Затронутые места:

- `tools/smoke_project_init_local_search_mcp.py:65-66`
- `tools/smoke_project_init_local_search_mcp.py:88-106`

Но проверки leakage слишком узкие:

- `str(workplace) not in snapshot_text` не ловит normalized slash form, parent temp root, drive/path fragments и поля вроде `local_path`/`resolved_path`;
- нет assertion, что snapshot `local_search_resources` содержит только `path_ref` и не содержит runtime-only `content_roots`;
- нет negative case для escaped concrete template registry entry.

## Confirmed Good

- Template snapshot production пишет metadata-only records с `path_ref`, без `content_roots`/`local_path`: `tools/processforge.py:9785-9818`, `9936`.
- MCP `pf.search` привязан к Ledger session/project и отказывает при project mismatch: `tools/pf_runtime/mcp_server.py:66-75`.
- `pf.search` требует fresh/fresh_with_updates snapshot перед search: `tools/pf_runtime/mcp_server.py:109-113`.
- `local_path` добавляется только в MCP runtime response после candidate file check: `tools/pf_runtime/mcp_server.py:128-144`.
- Документация корректно фиксирует, что `local_path` является private runtime navigation value: `docs/concepts/runtime-mcp.md:28-32`.

## Verification

Static review completed against allowed files only.

Smoke execution attempted:

```text
python -B tools/smoke_project_init_local_search_mcp.py
```

Result: blocked by sandbox/read-only temp permissions before product assertions ran:

```text
PermissionError: [WinError 5] Access denied: 'D:\\temp\\tmpjt74afyl\\allowed'
```

No product code was edited.