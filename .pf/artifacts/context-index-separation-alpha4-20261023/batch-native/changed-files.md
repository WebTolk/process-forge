# Изменённые файлы: batch-native

Статус: `ready_for_review`. Этап: implementation.

| Файл | Назначение |
| --- | --- |
| `src/processforge_core/resources/knowledge_batch.py` | Проверка batch-envelope, последовательные native-транзакции, сбор успешных catalogue ID и единственный итоговый callback индексации. |
| `tools/pf_cli/commands/knowledge_batch.py` | Тонкий адаптер YAML/Core, JSON или текстовый отчёт, переносимые коды ошибок и ненулевой exit при частичном либо итоговом сбое. |
| `tools/pf_cli/parsers/knowledge_batch.py` | Отдельный регистратор `knowledge-add-batch` с явными workplace/package/batch-file и read-only режимом по умолчанию. |
| `tests/context_index_separation/test_knowledge_batch.py` | 31 поведенческий сценарий для orchestration, CLI/parser и native authoring/recovery на синтетических fixtures. |

Служебные результаты: `change-summary.md`, `stdlib-source-check.json`,
`check_sources.py` и разрешённый append-only журнал роли. Отчёт assignment
возвращается через final-response delivery contract.

Точные SHA256 и размеры проверенных четырёх файлов находятся в
`stdlib-source-check.json`. Main, canonical maintenance owner, существующие
backend-файлы, документация и release delivery этим contributor не изменялись.
