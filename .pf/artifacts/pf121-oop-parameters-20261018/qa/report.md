**QA рефакторинга параметров: BLOCKED_ENVIRONMENT**

Дата: 2026-10-18. Проверен только согласованный source-only объём. В выполненных проверках расхождений не обнаружено; положительный QA-допуск не выдан, поскольку три smoke не достигли проверок продукта.

Точное назначение: `p121-params-qa-after-completed-implementation-test-only-the-parameter-re`. Run: `garage-p121-params-qa-after-completed-implementation-test-only-the-param`. Context: `p121-params-qa-after-completed-implementation-test-only-the-parameter-re-capsule`.

Существующий исходный CLI подтвердил `implementation/in_progress`, context `valid`, readiness `ready`, отсутствие блокеров и разрешения `read`/`write_artifact`. Контрольные суммы capsule, brief, frozen baseline и Core AGENTS совпали с prepared input. Переходы жизненного цикла не выполнялись.

| Проверка | Результат |
| --- | --- |
| Frozen old/new parity | PASS: 250/250 случаев, 0 расхождений |
| Независимые контракты defensive copies, provenance, ID quirks, stateless policy | PASS: 4/4 |
| Изолированный импорт прямого и скопированного Core | PASS: 2/2 отдельных процессов `-I -B`, без импортов CLI/Host |
| Старые определения и потребители пяти helper-имён | PASS: 0 совпадений в 538 Python-файлах `src`, `tools`, `bin`, `examples` |
| `smoke_parameter_cascade_resolution.py` | BLOCKED: `PermissionError [WinError 5]` при создании fixture |
| `smoke_parameter_assignment_capsule.py` | BLOCKED: тот же отказ до проверок продукта |
| `smoke_parameter_freshness.py` | BLOCKED: тот же отказ до проверок продукта |

Сравнение использовало обязательный `baseline-functions.json` от baseline `d2f8a856565e77b5f1a6d3026369e861800ccffb`, без загрузки старого CLI. Проверены значения и типы, рекурсивный порядок словарей, порядок и изменение переданного provenance, `None`-удаления, `str(key)`/`str(id)`, пустые списки, строгие маркеры `is True`, duplicate/delete ID. Включён 21 случай native exception: совпали типы, сообщения, порядок побочных эффектов и частичный provenance. Сохранена особенность: append не обновляет ID index, delete перестраивает его. Дополнительно проверены глубокие копии, независимость мутаций в обе стороны и отсутствие состояния policy; 80 случаев сгенерированы с фиксированным seed 121.

В обоих потребителях AST подтвердил прямой импорт owning module и вызов `ParameterMergePolicy().merge_maps`. Вывод поиска ограничен указанными активными каталогами; более широкий обход встретил посторонний недоступный fixture-каталог. SHA-256 трёх проверяемых продуктовых файлов оставались одинаковыми на протяжении проверок.

Основные smoke запускались без изменения скриптов в Python 3.14.3. `TMP`, `TEMP`, `TMPDIR` направлены в собственный `.pf/tmp/p121-parameters/qa`; фактический temp root проверен. Повтор в существующем Python 3.13.13 остановился на отсутствии `yaml`; отдельная минимальная fixture-проба в нём также воспроизвела WinError 5. Зависимости и права не менялись. Неочистившиеся временные fixtures остались только в собственном scratch.

Следующее действие координатора: повторить ровно три smoke в среде с доступным PyYAML и разрешённым созданием/очисткой fixtures. Полученные проверки не указывают на необходимость исправления продукта.

Машинные данные: `results.json`; подробные сравнения: `parameter-parity.json`; протоколы запусков: `smoke-results.json`, `smoke-results-py313.json`; журнал: `log.md`. Воспроизводимые QA-harness сохранены в собственном scratch как evidence. Продукт и постоянные тесты не редактировались.

Inventory проверяет владелец документации отдельно. Глобальная checksum-валидация, полный release suite, ZIP-content, archive/install, Runtime и connected/actual-host acceptance не выполнялись. Git, инфраструктура и вложенные агенты не использовались.