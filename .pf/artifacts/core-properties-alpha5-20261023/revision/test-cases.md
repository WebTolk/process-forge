# Выполненные случаи R03

Источник: frozen af68fecf; permanent Core suite97 passed, полный registered
pytest858 passed /7 прежних skips /383 subtests. Подробные raw receipts и точные
хеши собраны в test-report и portable source-assurance-summary.

| Обязанность | Проверенные случаи |
| --- | --- |
| Metadata reader/value | Собственный VERSION/manifest, strict UTF8, missing/malformed/unreadable/oversize/mismatch/race/partial metadata, bounded Git metadata и переносимые поля. |
| Ownership/lifetime | Frozen loaded, live installed, same label/different manifest build, fresh owner after update, default factory один раз при concurrent first calls, borrowed bootstrap и отсутствие Core->CLI/Host imports. |
| Consumer truth | Реальные Runtime status/doctor и MCP list/describe observer seams; loadedA/installedB требует restart/reconnect; новая наблюдающая CLI не подставляет свою loaded identity вместо remote. |
| Portable contract | State schema2/identity report1/provenance contract2, old schema1 без build остаётся unknown, malformed remote fields отклоняются runtime validation, контейнеры ответов свежие. |
| Existing contract | Полный старый корпус, CLI три строки, initialize/input schemas/annotations/signatures, Runtime protocol/component version, guard/evidence/identity/parity checks. |
| Distribution | Native source274 PASS; полный native extracted archive PASS; все1501 ZIP entries/1500 managed hashes; actual default composition, foreign cwd и Unicode/space/#/% relocation. |
| Quality | Registered Ruff/format/AST, strict owner/action-seam mypy, Google docstrings/Bandit, owner coverage97%; старые lint/type diagnostics сравнены с точным baseline, introduced0. |

Установленный Core, actual Runtime и genuine connected MCP не подтверждаются
этими source/archive cases. Они проверяются отдельным device Work.
