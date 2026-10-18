# Независимое ревью переноса правил в ООП-ядро

**Вердикт: source-only acceptance. Блокирующих замечаний не обнаружено.**

Дата проверки: 2026-10-18, завершение 18:32 UTC.  
Роль: `worker-p121-core-rules-review`.  
Baseline: `4ace0657958603e50446e875db8cc6b57d5edbe9`.

## Контекст и границы

Проверено точное Work:

- run: `garage-p121-core-rules-review-independent-clean-context-source-review-af`;
- assignment: `p121-core-rules-review-independent-clean-context-source-review-after-all`;
- context: `p121-core-rules-review-independent-clean-context-source-review-after-all-capsule`;
- стадия: `implementation`;
- контекст: `valid`, готовность: `ready`, блокеров нет.

Контрольная сумма контекста совпала с подготовленным входом: `sha256:edf581055fbdee858e7eacbac69dad53b51f3981fa3e90073d139b47f441904e`.

Прочитаны обязательный brief, замороженные алгоритмы, действующий контракт переноса, progressive OOP decision, инструкции Core, отчёт primary, verification, parity/smoke evidence и четыре отчёта исполнителей. Контрольные суммы указанных доказательств совпали с подготовленным входом.

Выполнены анализ Serena, чтение исходников, ограниченный локальный Git diff и независимые вычисления AST/SHA-256 в памяти. Продукт, артефакты, индекс, история и lifecycle не изменялись. Вложенные агенты, сеть, инфраструктурные операции и повторные fixture/full/archive проверки не использовались.

## Результаты проверки исходников

**Алгоритмы и интеграция.** Все 20 методов четырёх владельцев совпали по AST с функциями baseline после удаления `self`, обратного переименования методов и восстановления разрешённых вызовов. Замороженные тела также совпали с Git baseline. Разница хеша исходного baseline объясняется CRLF/LF: CRLF-представление Git-содержимого даёт заявленный frozen SHA-256.

Все шесть общих определений — `Check`, `check`, `safe_id`, `title_from_id`, эффективный поздний `as_list`, `string_list` — совпали с baseline по AST. Все восемь констант сохранили исходные значения, типы и порядок там, где он определён списком.

Для 962 оставшихся определений монолита независимое сравнение подтвердило только ожидаемые замены обращений к владельцам. Удалены именно 25 согласованных определений. Оба монолитных `as_list` сохранены.

**Семантические границы.**

- `Check` остаётся изменяемым dataclass с полями `level` и `message`; `check` вызывает `level.upper()`. Итоговый модуль содержит восстановленный `future annotations`.
- Authoring сохраняет обязательный `title`, свежие defaults, прежний выбор полей, вложенные ссылки и общий `return` между маршрутами.
- Evolution сохраняет shallow merging, truthiness, disabled-ветви, удержание privacy/apply policy, неизвестные поля согласно исходному алгоритму, порядок и сообщения проверок.
- Drivers сохраняет свежие документы, порядок рекурсивного обхода placeholders, обработку bool/int и исходных исключений, нормализацию `args`. Readiness проверяет документ без поиска или запуска executable.
- Sites сохраняет игнорирование `provider_key`, пробелы в непустом ID, приоритет overrides, поверхностную мутацию вложенной policy, ссылки на channels/parent/local data и использование прежнего `rel`.
- Владелец объявлений артефактов использует канонические `common.values` без изменения алгоритмов.

**Потребители и зависимости.** Поиск прежних 20 имён в продуктовых Python-файлах не нашёл оставшихся обращений. Проверены ссылки на новые классы и изменения обоих внешних smoke-потребителей. Монолит обращается к конкретным экземплярам; authoring создаёт конкретный `ProcessEvolutionPolicy`. В перенесённых владельцах нет обратного пути к монолиту через imports, callbacks или providers. Package initializers и `common.paths` не изменены.

**Документация и inventory.** Изменения EN/RU соответствуют фактическим владельцам и явно сохраняют неперенесённые обязанности и границу source-only. Inventory содержит семь обновлённых и шесть новых строк; 1312 прежних строк сохранены, удалений нет. Все 13 затронутых записей совпали с каноническим алгоритмом checksum, нормализующим текст в LF. Три заранее известных посторонних расхождения сохранены:

- `.pf/process-forge.yaml`;
- `tools/release_metadata_contract.py`;
- `tools/smoke_stable_update_manifest_points_to_release.py`.

## Проверенные доказательства и ограничения

`parity-results.json` содержит **245/245 PASS**, включая 20 случаев исходных исключений, проверки ссылок/мутаций, свежести defaults и прямого/скопированного Core без CLI/Host. Его source hashes соответствуют итоговым исходникам. Зависимости прямого Core дополнительно проверены по коду; динамический direct/copied прогон принадлежит primary и независимо здесь не повторялся.

`smoke-results.json` содержит десять успешных существующих smoke: authoring materialization parity, materializes evolve, evolve questions, evolve targeting, runtime driver registry, Codex worker governance, prepared execution context, update sites schema, update candidate discovery, builtin process catalog.

После smoke изменился только `common/checks.py`: восстановлен `future annotations`. Это отличие явно отражено в `annotation-correction.json`; итоговая parity повторена primary на окончательных исходниках. Поэтому десять smoke принимаются с указанной узкой дельтой, без утверждения об их повторном запуске на итоговом `checks.py`.

Контрольные суммы основных доказательств:

| Доказательство | SHA-256 |
|---|---|
| `primary/parity-results.json` | `d9329c90bde156bf27f33f58b54d9b4db1c843b30c9dc56de799a3677f55d0e1` |
| `primary/smoke-results.json` | `e3ba52bce89dc1afde7125a99eb17725f9a53dc4f3e7ddc0e4a964b8eee06404` |
| `primary/verification.json` | `af475e4b4c5332df6bce07b92018c3c9a4a1acc8353d8b28e17171e551e89e31` |
| `primary/annotation-correction.json` | `b29a21e434dfaee197dec6bebd88cef5a2febfe94c3b0ea07ec9a69ea6c9f8b7` |

Пути доказательств в таблице относительны `.pf/artifacts/pf121-oop-core-rules-20261018/`.

## Принятые фактические SHA-256

Хеши ниже вычислены по фактическим байтам файлов и повторно подтверждены перед завершением ревью. Все совпали с итоговым product manifest.

| Файл | SHA-256 |
|---|---|
| `tools/processforge.py` | `7c78ee188aa37c96a6d72bbfa81fb76a34cb8d61e9de21a9b3fadf54cb200ab5` |
| `tools/smoke_codex_worker_governance.py` | `b3f8cd951a10bd012c0092a84e30b54482e3a6f087d5e35cd9b4f7e108dec9dd` |
| `tools/smoke_prepared_execution_context.py` | `91c8a7e1b416aa1ef6e1b603bda002a26b12dd6349d8a2a8367777b14f59c867` |
| `src/processforge_core/common/checks.py` | `19c5bdd64249ed40ffb96452d6a5b04ddc3b187eba60cbe135dbbf9150365432` |
| `src/processforge_core/common/ids.py` | `ad4c6d38a0ba4a2da2cae741a02da7a2cd6229f65386bd7b29c1d864c1e356b8` |
| `src/processforge_core/common/values.py` | `6eccd5af14370433f8e49611f3a38f262a5f2a86ce9447f30ccfb51a3bde509c` |
| `src/processforge_core/process_catalog/artifacts.py` | `3c12bf127fc08105bddc2332cd6c21f8ad2118ef2af479948f211f101f9b7bd3` |
| `src/processforge_core/process_catalog/authoring.py` | `e2b4791ae5200d9a3404f654676fdfd13cabc4b5c3bc542ae7f2a2c9bafcc127` |
| `src/processforge_core/process_catalog/evolution.py` | `84fbfa98942a73a392c03ca8ceb3da39461e2b0e75dc7963a9d33bb45169a50f` |
| `src/processforge_core/runtime/drivers.py` | `b273cb7da6197b94596e62323dfca551eeb22664fc7d4d474968e3c62de12d25` |
| `src/processforge_core/maintenance/sites.py` | `4ed0097442f5b28ce62d67823bce071006676eeedf0781f5afaf07b4ff3596b7` |
| `docs/concepts/python-core-structure.md` | `c53c3562a7b383d6d67aff6c5a8848bf564544d4496c44b53bac7113ca0724a5` |
| `docs/ru/concepts/python-core-structure.md` | `61f3840afc42edb2e19a91f5990aa0215d39b492d233e48f7a65e3b987bf6c0c` |
| `checksums/processforge.sha256` | `434efd395679d5437db2bd76056019e25bae06a63d3d7b97d7f294e04fc8d1d9` |

Приёмка относится к указанным исходникам и ограниченным доказательствам. Archive/install/Runtime/connected-host acceptance не установлена; OOP-эпики остаются открытыми. Последующие изменения принятых файлов требуют соответствующего повторного ревью. Native transitions и поставка остаются обязанностью primary.