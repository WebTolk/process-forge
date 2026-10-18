Реализация завершена в пределах задания `p121-core-rules-authoring-implement-processauthoringdefinitionbuilder-an`.

Сначала добавлены общие функции:

- `common/ids.py`: точный `title_from_id`; существующие функции сохранены.
- `common/values.py`: поздний строгий `as_list` и исходный `string_list` с повторным вычислением `str`.

Затем создан `process_catalog/authoring.py` с `ProcessAuthoringDefinitionBuilder`: `defaults`, `normalize`, `build`, `normalize_transitions`, `materialize_responsibility_boundaries`. Сигнатуры сохранены с добавлением `self`; аргумент `title` остаётся обязательным. Конструктор создаёт конкретный `ProcessEvolutionPolicy` из нового модуля владельца.

Перенесённые алгоритмы структурно совпадают с замороженными исходниками после учёта переименований и замены внутренних вызовов. Сохранены создание свежих defaults, поверхностные ссылки, общий `return` между маршрутами, обработка неизвестных полей и порядок операций. Дополнительное копирование и валидация не вводились.

На `2026-10-18 18:18:17 UTC` все 13 проверок имеют статус PASS: синтаксис трёх файлов, AST четырёх общих функций, AST пяти алгоритмов и конкретная зависимость без импорта монолита. Результаты зафиксированы в `.pf/artifacts/pf121-oop-core-rules-20261018/authoring/checks.json`.

| Файл относительно `src/processforge_core/` | SHA-256 |
|---|---|
| `common/ids.py` | `ad4c6d38a0ba4a2da2cae741a02da7a2cd6229f65386bd7b29c1d864c1e356b8` |
| `common/values.py` | `6eccd5af14370433f8e49611f3a38f262a5f2a86ce9447f30ccfb51a3bde509c` |
| `process_catalog/authoring.py` | `e2b4791ae5200d9a3404f654676fdfd13cabc4b5c3bc542ae7f2a2c9bafcc127` |

Проверки ограничены синтаксисом и AST. Исполнение импортов, интеграционная parity и существующие smokes остаются основному исполнителю. Валидация authoring и потребители монолита не изменялись. Git-мутаций, lifecycle-переходов, вложенных агентов и постоянных тестов не было.