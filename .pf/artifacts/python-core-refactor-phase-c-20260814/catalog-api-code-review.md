# Catalog API Code Review

Статус: `PASS с условиями`.

Сверка выполнена по correction-артефакту `.pf/artifacts/python-core-refactor-phase-c-20260814/catalog-api-patch-correction.md:5-7,884-910`, по предыдущему review `.pf/artifacts/python-core-refactor-phase-c-20260814/catalog-api-review.md:25-34,76` и по текущему исходнику из разрешённого scope. Исполнение команд и runtime smoke не запускались; вывод ниже основан на read-only проверке кода.

## Подтверждено

- Прямой CLI bootstrap для `src` встроен в сам legacy CLI: `tools/processforge.py:32-43` вычисляет `repo_root`, добавляет `src` в `sys.path` до импорта `processforge_core`, затем инициализирует `ROOT`. Это закрывает confirmed blocker для запуска `python tools/processforge.py ...`.
- В reviewed slice один владелец `ProcessDefinitionRef`: класс определён только в `src/processforge_core/process_catalog/models.py:16-28`. Legacy CLI лишь импортирует его из core в `tools/processforge.py:45-53`, а runtime host использует core-resolver через тот же типовой seam в `tools/pf_runtime/host.py:115-128`.
- Новый catalog core не тянет `tools/` как compile-time зависимость: `src/processforge_core/process_catalog/service.py:6-8` зависит только от `processforge_core.common` и локальных моделей; `src/processforge_core/common/__init__.py:1-10`, `ids.py:1-8`, `paths.py:1-10`, `yaml_io.py:1-80` также self-contained.
- Порядок каталога сохранён в требуемом виде, включая вставку `official` перед первым `core`: roots объявлены в `src/processforge_core/process_catalog/service.py:121-143`, а `process_catalog_entries()` вставляет official-entries ровно перед первой `core`-веткой в `:185-193`.
- Семантика classification/role перенесена корректно: `process_catalog_metadata()` и `process_catalog_role()` в `src/processforge_core/process_catalog/service.py:28-57` сохраняют fallback по `status`, а также special-case для `INTERNAL_MAINTENANCE -> internal` и `DEPRECATED -> legacy_alias`.
- Override/duplicate warnings сохранены: `src/processforge_core/process_catalog/service.py:164-183` формирует предупреждение для user/custom override без `process_override.reason`; strict-эскалация до `STRICT:` есть там же, а legacy CLI по-прежнему поднимает такие strict duplicates в `FAIL` через `tools/processforge.py:14620-14629`.
- Семантика ошибки для неактивного official pack сохранена и в `resolve`, и в explicit guard: `src/processforge_core/process_catalog/service.py:261-269` и `:272-291` выдают `FAIL` с `pack-activate` hint.
- Host cache и lazy seam сохранены: rebuildable cache и lock находятся в `tools/pf_runtime/host.py:23-27`; lazy core import и mtime-based invalidation реализованы в `resolved_process()` (`:103-137`); lazy state/status остаётся в `load_state()` и status payload (`:323-338`, `:619-623`).

## Условия

- В legacy CLI осталась локальная copy семантики classification для validation/reporting surface: `tools/processforge.py:14036-14066` определяет собственные `PROCESS_CATALOG_CLASSIFICATIONS` и `process_catalog_metadata()`. Для Phase C catalog/resolve seam это не даёт немедленного расхождения, но это ещё одна точка будущего drift, если catalog classification rules будут меняться дальше.
- Формулировку “no core-to-tools dependency” нужно трактовать узко, в пределах extracted catalog slice. `src/processforge_core/process_catalog/*` действительно не зависит от `tools`, но `src/processforge_core/bootstrap.py:70-76` по-прежнему намеренно загружает legacy `tools/processforge.py` для runtime bridge и alias legacy core. Это соответствует approved correction boundary и само по себе не выглядит регрессией.

## Fail

- В разрешённом scope фактических fail по Phase C catalog/resolve extraction не найдено.