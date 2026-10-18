Реализация `KnowledgeCandidateTargetingPolicy` завершена в разрешённой области.

Созданы:

- `src/processforge_core/evolution/candidates.py`: 11 обычных методов и три исходные константы; зависимости импортированы из канонических `common` и `process_catalog.evolution`.
- `src/processforge_core/evolution/__init__.py`: только docstring, без импортов и реэкспортов.

Точное состояние Work проверено существующим CLI с заданными run/assignment/context: стадия `implementation`, контекст `valid`, готовность `ready`, блокеров нет. Контрольные суммы capsule и обязательных источников совпали.

Проверки пройдены: синтаксис обоих файлов; равенство AST всех 11 методов после нормализации имён и `self`; равенство AST трёх констант; канонические импорты и минимальный initializer. Сохранены исходные возвраты словарей по ссылке, fallback, преобразования и порядок вычислений, promotion/generalization, сообщения и порядок validation, условие `isinstance(evidence_count, int) and evidence_count > 1`. Обработка исключений не добавлена.

SHA-256:

| Файл | Хеш |
| --- | --- |
| `src/processforge_core/evolution/__init__.py` | `d291d2e8bc4aeb99fb2b4f18112982755c1941b0a51de5691b581129dae355ef` |
| `src/processforge_core/evolution/candidates.py` | `e1a3bea3bd50b7d8ec2f0434c645bcb72faf498bfb27d5980cb320f0d0897d4d` |

Доказательства и журнал: `.pf/artifacts/pf121-oop-core-services-20261018/candidates/verification.json` и `execution.md`.

Проверка ограничена AST и синтаксисом. Интеграция вызовов, динамическая assurance и независимое review остаются у основного исполнителя. Полный sanitizer, validation/export/lifecycle не изменялись. Git-мутации, удалённый доступ, инфраструктурные изменения, вложенные агенты, fixtures, постоянные тесты и lifecycle transitions не выполнялись.