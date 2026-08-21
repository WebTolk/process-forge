# Release Gate Audit: project-init/local-search MCP

## Вывод

Два smoke-теста уже находятся в стандартном release registry ProcessForge: в `tools/processforge.py` внутри `release_test_commands()` зарегистрированы:

- `smoke_project_init_local_search_mcp` -> `tools/smoke_project_init_local_search_mcp.py`, timeout `180`, layer `public`, `public_gate=true`.
- `smoke_project_init_acceptance` -> `tools/smoke_project_init_acceptance.py`, timeout `180`, layer `public`, `public_gate=true`.

Позиция в списке корректная: после snapshot/freshness smoke-проверок и до parameter/session/capability/specialization блоков. Это делает их частью обычного `release-test`, `release-test --public`, `smoke-all` и extracted archive validation.

## Что именно закрывают эти gate

`smoke_project_init_local_search_mcp` закрывает минимальный release-контракт для локального поиска и MCP:

- SQLite FTS5 search видит только snapshot-authorized resources.
- Stale snapshot определяется как `stale`.
- Внешний файл/секрет вне разрешенного root не попадает в результаты.
- Конфликтный pagination `limitstart` + `offset` дает `ambiguous_offset`.
- MCP `tools/list` содержит `pf.search`.
- `pf.search` возвращает `canonical_path`, `path_ref`, provenance и не протекает абсолютными путями.
- Cross-project call блокируется `session_project_mismatch`.
- Traversal/registry secret не находится.
- Repair без `apply` дает `apply_required`, с `apply=true` проходит до doctor `pass`.
- Project initialization с недопустимым `answers_path` дает structured `invalid_arguments`.
- Template search возвращает локальный template file, но не видит неразрешенный registry content.
- Public onboarding report не копирует полный приватный diagnostic.

`smoke_project_init_acceptance` закрывает полный acceptance-контракт:

- `project-onboard` с process/platform/specialization создает complete PF project.
- Public snapshot не содержит приватный workplace path.
- Parameter source для specialization маскируется как `<private-source-ref>`.
- `project-init-status` возвращает `complete`.
- `project-init-repair` восстанавливает deterministic PF-owned artifact, сохраняет semantic user content и не оставляет `.candidate`.
- FTS lifecycle различает `empty`, `stale`, `current`, `search_unavailable`.
- `pf.session_context` отражает актуальные stage obligations и меняется после перехода task stage.

## Как должны входить в release gate

Оставить оба теста как обычные `ReleaseCommand` в `release_test_commands()`:

```text
smoke_project_init_local_search_mcp  layer=public  public_gate=true  timeout=180
smoke_project_init_acceptance        layer=public  public_gate=true  timeout=180
```

Не нужно заводить отдельный workplace/tool/MCP registry. Здесь “release registry” - это список команд `release_test_commands()`, который питает `release-test`, `smoke-all`, `--only`, `--public` и archive extraction checks.

Рекомендуемая локальная проверка перед full gate:

```text
python tools/processforge.py release-test --only smoke_project_init_local_search_mcp --only smoke_project_init_acceptance --no-clean
```

Финальная release-проверка:

```text
python tools/processforge.py release-test --public
git diff --check
```

## Что остается для archive proof

После прохождения обычного release gate нужно собрать и проверить архив стандартной цепочкой:

```text
python tools/processforge.py release-pack --root . --output <release-zip>
python tools/processforge.py release-archive-test --archive <release-zip> --root . --extracted-test full
```

`release-pack` перед записью архива проверяет release hygiene, public cleanliness и checksum inventory, затем пишет deterministic ZIP и `.manifest.json` с Git commit/tree provenance, archive sha256, entry count и file hashes.

`release-archive-test --root . --extracted-test full` после этого доказывает:

- архив и manifest существуют;
- forbidden entries отсутствуют;
- manifest contract валиден;
- manifest file list совпадает с ZIP entries;
- ZIP entries совпадают с текущим release file set из root;
- file hashes в архиве и manifest совпадают с текущим root;
- extracted `bin/pf.py --help` и `tools/processforge.py --help` работают;
- внутри извлеченного архива запускается полный `release-test --public`, значит оба новых smoke gate повторно выполняются уже из release artifact.

## Фактическая проверка в этом audit

`python tools/processforge.py release-test --list` подтвердил присутствие обоих checks как `layer=public` и `public_gate=true`.

Точечный запуск двух checks сейчас не дал PASS: оба завершились `FAIL` на cleanup временного каталога с `PermissionError [WinError 5]` при выходе из `TemporaryDirectory`. По хвосту вывода сбой выглядит как Windows/temp cleanup issue, а не как assertion по project-init/search контракту, но release gate формально остается красным до устранения этого условия или до успешного запуска в окружении, где временные каталоги корректно удаляются.

## Риск

Главный остаточный риск не в регистрации release gate, а в воспроизводимости smoke-тестов на Windows: если `TemporaryDirectory` cleanup продолжит падать, full `release-test --public` и extracted archive test будут FAIL даже при рабочей бизнес-логике. Для release-доставки нужен чистый PASS этих двух checks внутри стандартной цепочки, а не только ручная инспекция кода.