**Статус: реализация завершена; требуется проверка primary.**

Назначение: `p121-core-contracts-updates-implement-updatesourcecontractpolicy-with-se`. Точный `pf.work.state` подтвердил совпадение project/run/assignment/context, валидность capsule, readiness `ready`, стадию `implementation` и отсутствие блокировок. Lifecycle-переходы не выполнялись.

Создан `src/processforge_core/maintenance/source_contracts.py` с классом `UpdateSourceContractPolicy` и семью методами:

- `requires_https`
- `remote_url_shape`
- `artifact_url_shape`
- `append_env_checks`
- `append_source_checks`
- `validate_registry`
- `sorted_sources`

Перенесены точные `UPDATE_SUBJECT_TYPES`, `CONTROL_CHAR_RE`, `ENV_REFERENCE_RE`. Сохранён `from __future__ import annotations`; используются canonical `common.checks.Check/check`, стандартные `re` и `urllib.parse.urlparse`.

Проверки прошли:

- Компиляция и загрузка модуля в памяти без записи bytecode.
- AST всех семи методов совпадает с baseline после переименования и добавления `self`.
- Сигнатуры связанных методов, `__annotations__` и разрешённые `get_type_hints` совпадают: 7/7.
- Текст и AST трёх констант, значения множеств, regex patterns/flags совпадают.
- Подтверждена идентичность импортированных canonical `Check/check`.

AST-сравнение подтверждает сохранение исходной структуры мутаций списка, различий типов/defaults/truthiness, допуска bool priority, порядка URL-проверок и исключений, сообщений, обработки дубликатов и стабильной сортировки.

SHA-256 изменённых файлов:

| Файл | SHA-256 |
|---|---|
| `src/processforge_core/maintenance/source_contracts.py` | `d69a03cd163c6ea5f696658863e0cae886624218db292376833dff8f17848a6f` |
| `.pf/artifacts/pf121-oop-core-contracts-20261018/updates/checks.json` | `59362de385d46c5668b67781af0c4d4f6440e539a1cf8658c6e91a0fbef26f39` |
| `.pf/artifacts/pf121-oop-core-contracts-20261018/updates/log.md` | `60ee54b4539fefa015b770712415b097d1454f7c9ce6d17e555ed1ef80831021` |

Проверен baseline `201ed9a677aca13d5df53d6de78b09fbe46bcf47`; SHA-256 `baseline-functions.json`: `619be0a48fa32c924b27170449a3c3e16acd5fff5e5d346898822dc4d3668ee0`.

Ограничения: поведенческие сценарии и caller migration не выполнялись; их доказательство, независимый review и native transitions остаются primary. Schema validators, network/auth policy и legacy-поведение не изменялись. Git-мутаций, remote access, инфраструктурных изменений, вложенных агентов, fixtures и постоянных тестов не было. Scratch не создавался.