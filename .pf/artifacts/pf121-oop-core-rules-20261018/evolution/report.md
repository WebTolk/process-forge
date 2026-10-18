Статус: реализация завершена в разрешённом scope.

Назначение: `p121-core-rules-evolution-implement-exact-mutable-check-dataclass-plus-c`. Точное Work state подтвердило этап `implementation`, действительный контекст и отсутствие блокеров.

Изменены только два продуктовых файла:

- `src/processforge_core/common/checks.py` — создан первым; содержит исходный изменяемый dataclass `Check` с полями `level`, `message` и фабрику `check`, вызывающую `level.upper()`.
- `src/processforge_core/process_catalog/evolution.py` — создан `ProcessEvolutionPolicy` с обычными методами `default_block`, `normalize_block`, `validate_block`; перенесены четыре исходные set-константы `EVOLVE_*`. Используются канонические `Check/check` и `common.values.string_list`.

Проверки: PASS.

- Контрольные суммы brief и baseline совпали с prepared input.
- Оба модуля компилируются без записи bytecode.
- AST `Check/check` точно совпадает с baseline.
- AST трёх методов точно совпадает после обратной адаптации только имён и `self`; сохранены операции слияния и мутации, truthiness, обработка disabled, порядок проверок и сообщения.
- AST четырёх констант совпадает, тип `set` сохранён.
- Проверены канонические импорты; существующий `string_list` совпадает с baseline по AST.

SHA-256:

| Файл | SHA-256 |
|---|---|
| `src/processforge_core/common/checks.py` | `4b135f054d1f3b1b88c1a88ba3c8a5f5942155b216110de8aedcf2256c5e018c` |
| `src/processforge_core/process_catalog/evolution.py` | `84fbfa98942a73a392c03ca8ceb3da39461e2b0e75dc7963a9d33bb45169a50f` |

Действия и результаты записаны в `.pf/artifacts/pf121-oop-core-rules-20261018/evolution/log.md`.

Ограничения: поведенческая parity, проверка direct/copied Core и существующие smokes остаются primary. Постоянные тесты и fixtures не создавались. Новые lifecycle, approval, candidate или knowledge возможности не добавлены. Git mutations, remote access, инфраструктурные действия, вложенные агенты и lifecycle transitions не выполнялись.