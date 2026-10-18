# Независимое ревью Core services

**Решение: ACCEPTED для проверенного среза исходников. Блокирующих замечаний не обнаружено.**

Проверка завершена: 2026-10-18, 19:02:48 UTC.  
Роль: `worker-p121-core-services-review`.

- Run: `garage-p121-core-services-review-independent-clean-context-source-review`
- Assignment: `p121-core-services-review-independent-clean-context-source-review-after`
- Context: `p121-core-services-review-independent-clean-context-source-review-after-capsule`
- Baseline: `0a8b5029a1cf5cd1afc0e33d545af6351b4e7261`

## Контекст и основания

Существующий CLI `work-state` вызван с точными селекторами назначения: состояние `implementation/in_progress`, контекст `valid`, readiness `ready`, блокеров нет. SHA-256 капсулы совпал с подготовленным входом:

`21df100ac98b2519e5e120537680729984203b7130199d231e5a32af22a8bd89`.

Совпали контрольные суммы snapshot и всех 13 обязательных источников. Прочитаны brief, migration contract, progressive decision, правила Core, primary report, verification/parity/smoke evidence и четыре отчёта исполнителей. Полный `baseline-functions.json` сопоставлен с исходниками зафиксированного Git baseline.

Serena/IDE MCP недоступны; использованы ограниченные файловые чтения, анализ Python AST и локальные Git-команды без мутаций.

## Результаты проверки

| Область | Результат |
| --- | --- |
| Presentation и обратная проекция | Проверены пять методов и каноническая функция coordination |
| Runtime driver catalog | Проверены девять методов и конкретная композиция reader |
| Candidate targeting | Проверены одиннадцать методов |
| Update selection и assessment | Проверены пять методов |
| Константы | Проверены все четыре перенесённых определения |

Все **31 алгоритм** совпали по AST с исходниками baseline после предусмотренных преобразований имени, `self` и конкретных зависимостей. Сохранены сигнатуры, defaults, аннотации, последовательность операций, строки и выражения, порождающие исходные ошибки.

Прежнее содержимое `ProcessAuthoringDefinitionBuilder`, включая конструктор и методы, сохранено побайтно. Добавлен только `from_definition`.

После удаления перенесённых определений и обратной нормализации новых вызовов весь оставшийся AST монолита совпал с baseline: сохранено **931 определение функций и классов**. Поиск потребителей в Python-исходниках baseline выявил монолит и MCP; оставшихся обращений к удалённым внутренним именам не найдено. Coordination импортируется от канонического владельца. Устаревшие wrappers и aliases не добавлены.

### Семантика и зависимости

`RuntimeDriverCatalogReader` сохраняет переданный корень без преобразований и I/O, создаёт конкретные `YamlDocumentReader(_parse_simple_yaml)` и `RuntimeDriverDefinitionPolicy`. Нормальная композиция не требует CLI/Host или объекта монолитного Core.

Сохранены порядок реестров, первое существующее совпадение, обработка прямых путей, builtin fallback с копированием, перезапись ID при построении списка, сортировка и `setdefault("_source_path", ...)`. Проверка существования документа предшествует строгому чтению. Чтение файлов остаётся актуальным; повторное использование parsing зависит от содержимого, включая изменение при прежних размере и mtime. Проверены соответствие строгих YAML-ошибок и эквивалентность fallback-парсеров.

В перенесённых обязанностях не обнаружено обратного выполнения через монолит, transport, callback/provider или универсальный объект Core. Переиспользованы существующие канонические примитивы.

Candidate policy сохраняет ссылки на исходные вложенные словари, fallbacks, promotion/generalization и порядок validation. Условие broad-scope evidence остаётся `isinstance(evidence_count, int) and evidence_count > 1`.

Update policy сохраняет обе формы manifest, заимствование вложенных объектов, общий `subject` внутри соответствующей группы версий, стабильную сортировку и прежнее различие обработки warnings при пустом и непустом выборе. Renderers сохраняют тексты, переводы строк и eager-вычисление default expressions.

Исправление `future annotations` в candidates объяснено в `annotation-correction.json`. Итоговый файл соответствует исправленному хешу; первоначальный отчёт исполнителя сохранён как историческое доказательство.

### MCP, документация и inventory

Весь MCP-файл совпал с baseline после единственной ожидаемой замены блока `registered_driver_ref`:

- проверка `driver_id` выполняется перед ленивым импортом;
- reader получает только значение `core.ROOT`;
- привязанные project/workplace, ошибки и разрешение итогового пути сохранены;
- bootstrap, действия, схемы и остальные байты файла не изменены.

Документация EN/RU соответствует фактическим владельцам и оставшимся границам миграции.

Inventory изменён ограниченно: **5 обновлённых и 7 новых строк**, без удалений; **1320 прежних строк сохранены**. Все затронутые строки совпали с нормализованными байтами файлов. Известный посторонний drift сохранён. Различие raw-хеша монолита и его inventory-хеша обусловлено CRLF/LF и подтверждено отдельно.

## Доказательства assurance

Проверены сохранённые receipts primary и их привязка к окончательным исходникам:

- **247/247 parity**, включая 27 случаев исходных исключений: presentation — 40, candidates — 122, updates — 45, driver I/O — 34, MCP binding — 4, прямой/скопированный Core — 2.
- **10/10 существующих smoke** завершились успешно: authoring materialization/evolve questions, driver registry, MCP action tools, четыре candidate smoke, update discovery и notifications.
- Все хеши исходников в parity/smoke evidence совпадают с итоговым manifest.

Reviewer независимо выполнил статическое сравнение, компиляцию owners в памяти, проверку потребителей, ограниченного diff и inventory. Fixture/smoke-наборы повторно не запускались.

## Зафиксированные SHA-256

Ниже приведены хеши фактических байтов файлов. Финальная повторная сверка подтвердила стабильность всех 13 файлов.

| Файл | SHA-256 |
| --- | --- |
| `tools/processforge.py` | `9949c90f0e0bf59259127cb475f6404cd19bd7f8c7bdabe4f1c7becdca37ac2f` |
| `tools/pf_runtime/mcp_server.py` | `bad15ce0a1e82773b5de636b1bc49aceeabfb95f3b242113011ff269e771debf` |
| `src/processforge_core/process_catalog/authoring.py` | `99abdb6ba983f6f77f1b7a22d3ca9b3267c26af1f1620cf8716d9a50af5125a2` |
| `src/processforge_core/process_catalog/presentation.py` | `6383c251dcd5f8801810083f8d73c90351d433667c00111e64b9292c921a4b88` |
| `src/processforge_core/process_catalog/coordination.py` | `98e4edee5f6f161b50698735e30945af4ead15832992c57fec340484812b0676` |
| `src/processforge_core/runtime/catalog.py` | `183f370372d3a840a38be677925a2744525308febd2e420fd3cd936261b25336` |
| `src/processforge_core/evolution/__init__.py` | `d291d2e8bc4aeb99fb2b4f18112982755c1941b0a51de5691b581129dae355ef` |
| `src/processforge_core/evolution/candidates.py` | `0596fe7f9b8affc83c6a061972505f531a8974a823166b47dac6caf4b23d7fa8` |
| `src/processforge_core/maintenance/versions.py` | `64cd8e795d9b63c178ea21fb2b3038d8d2c6326c60d98d25adb1e7bac5cb66dc` |
| `src/processforge_core/maintenance/presentation.py` | `f678df2822444cea88d16a0b74f2786f8bbd5f390abfd7985ce47e8ce2c896e1` |
| `docs/concepts/python-core-structure.md` | `f7f3494f9d18c341745e5f3eafa713b2fb82a1faf534e3825ca553a8498d593a` |
| `docs/ru/concepts/python-core-structure.md` | `472e99968a93fa82b1d9860d686bc2a2b6e75563f48a2eb996b07e18c608a497` |
| `checksums/processforge.sha256` | `29bb24a96f0e0787e28f80e70ff0adb7a4f1bbbb26317d8ea8e29bc1f06dd2b7` |

## Границы приёмки и передача

Принят только описанный срез исходников с сохранением внешнего контракта 1.2.0. Archive/install, фактическое исполнение Runtime и connected-host не квалифицированы. OOP-эпики остаются открытыми.

Продуктовые файлы, index, история Git и remotes не изменялись. Инфраструктурные действия, вложенные агенты и lifecycle transitions не выполнялись. Native transitions и дальнейшая доставка остаются у primary. Любое последующее изменение зафиксированных файлов требует проверки затронутой части.