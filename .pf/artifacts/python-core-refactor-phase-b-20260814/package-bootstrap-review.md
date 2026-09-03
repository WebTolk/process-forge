# Review: Phase B package/bootstrap foundation

## Вердикт

**PASS с условиями (`pass_with_conditions`)**

Фундамент Phase B в текущем виде выглядит корректным: bootstrap seam вынесен в `src/processforge_core`, legacy core по-прежнему сосредоточен в `tools/processforge.py`, direct-script адаптеры больше не тащат старый `sys.path`/`import_module("processforge")` bootstrap, а `pf_runtime.host` и `pf_runtime.service` грузятся как нормальные package modules. Критических расхождений со спецификацией и baseline по самому import/bootstrap seam я не вижу.

## Что подтверждено

1. **Direct-script shim достижим и централизован.**
   В обоих адаптерах есть минимальный локальный loader, который по `__file__` находит `src/processforge_core/bootstrap.py`, загружает его через `importlib.util.spec_from_file_location(...)` и вызывает `bootstrap_runtime(__file__)`: `tools/pf_runtime/mcp_server.py:23-38`, `tools/pf_runtime/codex_hooks.py:28-43`.
   При этом в разрешённой области больше нет старого adapter-level bootstrap через `sys.path.insert(...TOOLS_ROOT...)` и `import_module("processforge")`; статический поиск по allowed files совпадений не дал.

2. **Identity legacy-модуля сведена к одному object внутри bootstrap-пути.**
   `src/processforge_core/bootstrap.py` задаёт два имени (`processforge_core._legacy_processforge` и `processforge`) и привязывает их к одному и тому же `module` object, включая reuse через `_cached_legacy_core(...)`: `src/processforge_core/bootstrap.py:12-13`, `38-67`.
   Это подтверждается и заложенным smoke-assertion: `tools/smoke_processforge_core_package_bootstrap.py:47-65`.

3. **`pf_runtime.host` и `pf_runtime.service` импортируются как package modules, а не как file modules.**
   Bootstrap централизованно делает importable `src` и `tools`, затем вызывает `importlib.import_module("pf_runtime.host")` и `importlib.import_module("pf_runtime.service")`: `src/processforge_core/bootstrap.py:70-76`.
   Внутри самих модулей используются относительные package imports: `tools/pf_runtime/host.py:20`, `tools/pf_runtime/service.py:27-28`.

4. **Непреднамеренного domain extraction не видно.**
   `src/processforge_core/__init__.py` экспортирует только `RuntimeBootstrap` и `bootstrap_runtime`: `src/processforge_core/__init__.py:1-5`.
   В `bootstrap.py` нет переноса process/domain-логики; это именно import/bootstrap seam. Runtime-команды по-прежнему проксируются в legacy core через `sys.modules[__name__]`: `tools/processforge.py:18384-18507`.

5. **Поведение адаптеров по смыслу сохранено.**
   `mcp_server.py` по-прежнему отвечает за `initialize`, `tools/list`, `tools/call`, но теперь берёт `core` и `host` из `runtime`: `tools/pf_runtime/mcp_server.py:41-84`, `87-103`.
   `codex_hooks.py` по-прежнему нормализует hook event, пытается доставку через runtime и откатывается в `host.ingest_event(...)`: `tools/pf_runtime/codex_hooks.py:73-107`.
   Это соответствует baseline-описанию старого поведения: `.pf/artifacts/python-core-refactor-phase-b-20260814/bootstrap-baseline.md:20-44`.

6. **Windows launcher/input contract не сломан статически.**
   `bin/pf.py` всё ещё запускает legacy CLI как отдельный процесс и на Windows использует `os.spawnv(...)`: `bin/pf.py:18-33`.
   Runtime daemon по-прежнему стартует `tools/processforge.py runtime serve ...` через `sys.executable`, а на Windows сохраняет `CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS`: `tools/pf_runtime/service.py:497-525`.

## Условия и остаточные замечания

1. **Минимальный local shim в direct-script адаптерах остаётся необходимым.**
   Это не дефект текущей реализации, а архитектурное условие Phase B: пока `tools/pf_runtime/mcp_server.py` и `tools/pf_runtime/codex_hooks.py` поддерживаются как direct-script entrypoints, полностью убрать path-based первичную загрузку `bootstrap.py` нельзя. Это совпадает с предыдущим review: `.pf/artifacts/python-core-refactor-phase-b-20260814/package-bootstrap-spec-review.md:5-10`, `45-49`, `61-68`, `112-116`.

2. **Smoke quality достаточна для seam, но не полна относительно characterization matrix.**
   Текущий smoke-файл хорошо проверяет:
   - module identity,
   - bootstrap reuse,
   - package imports,
   - `mcp_server.py --help`,
   - безопасный ignore для hook вне PF-проекта.
   См. `tools/smoke_processforge_core_package_bootstrap.py:46-90`.

   Но он **не** покрывает отдельными assert/exec:
   - `python bin/pf.py --help`,
   - `python tools/processforge.py --help`,
   - MCP `initialize`/`tools/list` roundtrip,
   - `runtime start|status|stop` path,
   - живую Windows detached-subprocess семантику.

   Эти проверки перечислены в baseline/spec как ожидаемые characterization checks, но в самом dedicated smoke script их нет: `.pf/artifacts/python-core-refactor-phase-b-20260814/bootstrap-baseline.md:42-44`, `.pf/artifacts/python-core-refactor-phase-b-20260814/package-bootstrap-patch.md:462-466`.

## Граница проверки

Проверка в этом assignment была **read-only и статической** по разрешённым файлам. Я не переисполнял live-команды из baseline/spec, потому что это потянуло бы импорты и чтение файлов за пределами `allowed_read_files`. Поэтому вердикт подтверждает корректность seam по коду и встроенным smoke-assertions, но не заменяет отдельный живой smoke на Windows/runtime lifecycle.