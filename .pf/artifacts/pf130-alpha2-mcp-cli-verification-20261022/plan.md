# Проверка MCP и CLI после alpha2

2026-10-22. Пользователь поручил погрузиться в проект и проверить обновлённые
MCP и CLI по последней выполненной задаче. Основа — завершённая доставка
pf130-alpha2-release-correction-20261022, commit
26dab5ad6783ce0aa56828f86d7f9453e626c638, source
fe0f15072538fee9525792ae5b8c1e634b13a928, update
core-update-20261022T162745Z.

Отдельная Work имеет режим analysis_only: разрешены чтение и собственные
артефакты/журнал; изменение продукта запрещено. Assignment, capsule и текущий
pf.work.state прочитаны; checksum capsule
26a7742f760d39e368181169d82e6a4e6f79f3fac9e078c03c131b4906daa9f9,
validation=valid, execution_readiness=ready. Snapshot
ctx-20261021-162229-c46ea2 свежий, policy=continue. Выбрана компактная проверка
существующего поведения в software-feature-development@1.2.1. Модель предметной
области и архитектура не меняются, реализация не требуется.

Порядок: прочитать startup contract и последнюю доставку; сопоставить контексты
и exact Work; проверить версии, установленный manifest и hashes; сравнить
каталог и schemas MCP/CLI; прочитать реальные project usage summary/details;
проверить происхождение подключённого процесса и read-only Runtime status;
записать evidence/report, закрыть Work, доставить только собственные документы.

Критерий приёмки: ответы фактически подключённого MCP согласованы с CLI на
одном snapshot; новые CLI usage schema совпадают; реальные totals не расходятся;
installed Core соответствует манифесту. Неизвестные provenance и coverage
сохраняются как ограничения, а обнаруженные расхождения — как findings.

Источники: .pf/AGENTS.md, .pf/process-forge.yaml, свежие pf.context/work.state,
assignment/capsule, report/device-result/installed-functional последней
доставки, docs/ru/concepts/usage-accounting.md, действующие CLI parser/action
contracts, tools/processforge.py и tools/pf_runtime/mcp_server.py.
Serena использована для чтения структуры и точечного поиска; Work resource
resolve/search подтвердили разрешённые материалы. Поиск usage accounting в
Work дал ноль результатов, поэтому использован известный файл документации.
Python-код не меняется: pytest/Ruff/mypy для изменения реализации неприменимы;
поведенческая проверка выполняется существующими CLI/MCP операциями и сравнением
JSON. Независимая реализация/делегирование не требуются.

Запрещены повторная установка, refresh, restart/repair Runtime/MCP, запуск
воркеров, import/replay и изменение прежних утверждённых свидетельств. Общая
stable/public квалификация и native Kimi capture не входят в эту проверку.
