# p121-params-docs — отчёт

Дата: 2026-10-18. Статус: выполнено в выделенной области.

Точное состояние Work проверено через существующий source CLI: контекст `valid`, готовность `ready`, блокирующих ограничений нет, этап `implementation`. Identity и checksum капсулы совпадают с prepared input. Обязательные inline-источники прочитаны.

## Изменения документации

Обновлены только:

- `docs/concepts/python-core-structure.md`;
- `docs/ru/concepts/python-core-structure.md`;
- `checksums/processforge.sha256`.

В EN/RU справочниках добавлены владелец `configuration.parameters.ParameterMergePolicy`, его метод `merge_maps` и два прямых потребителя: `tools/processforge.py:add_parameter_source` и `work.context.build_context_fields`.

Явно сохранено описание legacy-зависимостей `build_context_fields`: вызовы `core.add_parameter_source`, `core.parameter_payload`, нормализация Assignment, snapshot paths/checksums, project/workplace resolution, source capture и coordination. Полный компилятор контекста остаётся частично зависимым от монолита.

## Точные изменения инвентаря

Использован существующий `sha256(released_content(path))` из `tools/validate-process-forge-checksums.py`: CRLF нормализуется в LF для содержимого без NUL; содержимое с NUL хешируется без преобразования.

| Файл | Прежний SHA256 | Новый SHA256 |
| --- | --- | --- |
| `docs/concepts/python-core-structure.md` | `cde26e539cdb453e90c09a823a5a1205e823f670e9a7a0acc93373af0da8522c` | `306bbb8ad150a3dd8846facbe3e3762a2d1091e0582fa86b116e14be82098cb2` |
| `docs/ru/concepts/python-core-structure.md` | `ef1b9524634ef613072c910935bc1fc0719405af7a697b20decc92ee01b17923` | `ac46e9dd4e8f8f527f0218e18d8ccc0e85af72ca11a80b4f4d09c4eec555b522` |
| `src/processforge_core/work/context.py` | `a8757b008f7b3b85934bea2e8c9464e5507a086e28210aed476ce5683751abc1` | `b5ccb12c95ef258f6461a88f7ae48bc78411dfe8e2ae096c177d038219f37b81` |
| `tools/processforge.py` | `540bd52f04de93ec4636a6f3210f0331830462bbdd6a0407acc857f8945fb4dc` | `9ace7a979264eee2c0b18bc79387bd2c3cd9214b57e2c5c35f9e4a3262efcf0d` |
| `src/processforge_core/configuration/parameters.py` | Запись отсутствовала | `c8b0dd01b30012455e35f27cec02681ad50f773461eec196349fac303f246634` |

Итого: четыре замены, одно добавление, удалений нет; количество записей — 1316 → 1317. Сам checksum inventory исключён helper из собственного покрытия. Остальные 1312 строк сохранены побайтно, включая порядок и прежние хеши.

## Проверки и остаточные ограничения

Целевые проверки — PASS:

- Все пять целевых записей совпадают с результатами существующего helper.
- В каждом справочнике добавлено ровно 25 строк; удалений нет, UTF-8/LF сохранены.
- Serena и AST подтверждают прямые импорты/вызовы двух потребителей и оставшиеся legacy-вызовы компилятора.

Команда `python tools/validate-process-forge-checksums.py --root . --check` завершилась с кодом 1 исключительно из-за трёх заранее обнаруженных расхождений вне задания:

- `.pf/process-forge.yaml`;
- `tools/release_metadata_contract.py`;
- `tools/smoke_stable_update_manifest_points_to_release.py`.

Их записи намеренно сохранены; полный инвентарь не перегенерировался.

Журнал и точные evidence представлены в `work-log.md` и `inventory-changes.json`. Проверки относятся к исходникам, документации и checksum inventory. Архив, установленный Core, Runtime и подключённые хосты не квалифицированы. Git, инфраструктурные изменения, вложенные агенты и lifecycle transitions не выполнялись.