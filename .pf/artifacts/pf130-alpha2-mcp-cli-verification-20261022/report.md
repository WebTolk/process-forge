# MCP и CLI после установки 1.3.0-alpha2

2026-10-22. Проверенные операции работают согласованно. Исходный и установленный
CLI показывают ProcessForge 1.3.0-alpha2. Фактически подключённый MCP отвечает,
видит новые CLI usage commands и корректно читает/создаёт ограниченную Work.
Последняя release Work отдельно прочитана с точными selectors:
run_completed, assignment done, capsule valid; она не возобновлялась.

| Проверка | Текущий результат |
| --- | --- |
| Context source CLI / installed CLI / connected MCP | fresh / continue, snapshot ctx-20261021-162229-c46ea2 |
| CLI readiness | ready, blockers отсутствуют |
| Installed Core | alpha2, 1476 managed files, incomplete_update=false |
| Проверка SHA-256 всех managed files | 1476/1476 совпали, missing=0, mismatched=0 |
| Каталог действий source / installed / MCP | Полное равенство JSON для query=usage, 10 CLI commands, одинаковые schemas/fingerprint |
| Реальные usage summary source / installed | Полное равенство JSON, кроме времени формирования as_of |
| Реальные usage details | 3 записи, каждая привязана к project/Work/attempt |
| Runtime read-only status | health/readiness=ready; director, inspector, ledger, metrics, projection fresh/ok |

Данные учёта: input 3673006, output 43020, total 3716026 токенов;
3437440 cache-read входят в input. Execution time 1414.7816799001303 s имеет
качество lower_bound. Occupied time 762.006762 s имеет качество partial.
Coverage complete=false для трёх наблюдаемых источников; общая активность
устройства не объявляется известной. Import/replay в этой проверке не выполнялись.

MCP запущен через установленный entrypoint в 16:47:18 UTC, после update
core-update-20261022T162745Z. Совпадение установленного манифеста, времени запуска
и catalogue/schema показывает согласованность с обновлённой установкой.
Это проверка живого подключения. Протокол самостоятельно не возвращает точный
loaded-module build/hash: connected_host_build остаётся unknown, поэтому
криптографическая аттестация памяти процесса не заявляется.

Обнаружены ограничения и расхождения:

- Action catalogue и monitor cli_version сообщают 1.2.0, тогда как VERSION,
  release manifest и команда version показывают alpha2. Точечная проверка
  tools/processforge.py:460 подтвердила PROCESSFORGE_VERSION = "1.2.0";
  MCP initialize также использует эту константу. Канонические Core properties
  уже зарегистрированы отдельной planning-only задачей; здесь код не исправлялся.
- Новых MCP usage query tools нет. Это соответствует текущей документации:
  MCP, TUI и REST названы будущими клиентами общего scoped AccountingService.
  Проверенный MCP каталог обнаруживает CLI contracts, но не исполняет usage query.
- Temporary-files observation остаётся partial/time_limit; scheduler job
  temporary_files — unknown. Sessions/work/workers metrics имеют partial coverage.
- Derived project reports stale: project-profile до сих пор указывает 1.1.0.
  Эти отчёты не использованы как актуальное доказательство версии.
- Legacy planning card Core properties имеет неполный старый contract; её
  read-only состояние не мешает новой scoped verification Work. Реализацию
  следует начинать через явно scoped successor, сохранив planning-only исходник.

Методика и scope — plan.md; структурированное свидетельство — evidence.json.
Команда версии использует subcommand version; проба --version была отклонена
действующим parser и не считается регрессией. Python-реализация и установленные
файлы не менялись, поэтому исходные QA gates не повторялись. Проверены текущие
native CLI operations, connected MCP, hashes и равенство JSON. Полный stable/public
release test, новый worker capture и native Kimi capture не проводились.

Вердикт: PASS для проверенных MCP/CLI операций alpha2 с указанными ограничениями
version metadata, provenance и coverage. Повторная установка или перезапуск
для этой проверки не потребовались.
