Результат: **PASS в пределах assignment semantics**.

Assignment: `p121-core-foundations-semantics-create-project-platform-validation-py-pl`.
Run: `garage-p121-core-foundations-semantics-create-project-platform-validatio`.
Context: `p121-core-foundations-semantics-create-project-platform-validation-py-pl-capsule`.

Точное состояние прочитано через SOURCE CLI с указанными selectors: implementation, контекст valid, readiness ready, blockers отсутствуют. Закреплённые brief, baseline, девять архитектурных входов, Python material и frozen зависимости изучены. Lifecycle-переходы не выполнялись.

Созданы только два продуктовых модуля:

- `src/processforge_core/project/platform_validation.py`: `PlatformContractValidationService(distribution_root: Path)` с методом `validate(workplace_root, data, platform, *, platform_resolution=None)`. Конструктор явно собирает существующие конкретные owners и `TemplateCatalogService`; действительный workplace передаётся в операцию. Сохранён весь алгоритм исходной `platform_contract_semantic_checks`.
- `src/processforge_core/common/policies.py`: самостоятельные `policy_entries` и `policy_id_matches`, без класса; сохранены borrowed-словари, `re.fullmatch`, short-circuit и native invalid-regex error.

Сохранены future annotations, сигнатуры и строковые аннотации, все литералы, сообщения и CLI hints, порядок checks/чтений, required/optional/recommended semantics, наследуемые ресурсы, missing/cycle/stack observations, fallback для ложного `platform_resolution`, повторные наблюдения каталогов и отсутствие мутации входного документа. Новых политик, кэшей, DI-механизмов или обратных зависимостей от Main/Host нет.

Проверка полного AST допускает только явные замены receivers на поля owning service, `ROOT` на `self.distribution_root`, `template_manifest_path` на `self._templates.manifest`, переименование функции в `validate` и добавление `self`. Совпадение подтверждено для всех трёх исходных функций, каждого узла и упорядоченных литералов; сигнатуры и аннотации также сравнены. Пятнадцать неизменённых frozen owners совпадают по исходным байтам и AST. Mutable peer-файлы не читались; `common.values.list_value` использован из frozen входа.

Ровно пять синтетических сценариев прошли с полным сравнением результатов, трасс и ошибок оригинала и переноса:

1. Borrowed dict identity, видимость мутации, свежие пустые списки, точное совпадение id, fullmatch и native regex error.
2. Required/recommended ресурсы, ослабление родителя, missing platform, цикл и fallback пустого resolution; пять отдельных package index и пять template observations со сменой доступности повторяющегося id.
3. Переданный непустой resolution обходит resolver; пустой hints-список сохраняет WARN, пустой stack — FAIL.
4. Некорректный regex останавливает выполнение после первого check и чтения policy, до последующих platform reads.
5. Некорректная ссылка сохраняет native `KeyError('id')` и прежний порядок checks до отказа.

Причины и контексты исключений совпали. Конструктор со stubs выполняет только сборку зависимостей; policy получает явный distribution root, selection — исходный объект resolution. Исходники скомпилированы без импорта продуктовых модулей. Доказательства и полные наблюдения находятся в `proof.json`, воспроизводимый сценарий сохранён как `native-proof.py`, ход работы — в `log.md`; временный генератор удалён.

Итоговые SHA256 исходных байтов:

| Файл | SHA256 |
| --- | --- |
| `src/processforge_core/common/policies.py` | `8b9ba9bbb9a778b8ec306b182fd4e277dfbf5b7fc884b506737ea2ab928abb21` |
| `src/processforge_core/project/platform_validation.py` | `d7d3ecffbd0d5d4687a71b4cb21fad5dcc881ea4232c15e4f0e10829426b6ede` |
| `proof.json` | `3c629293b2900bfd85f2f8280f71ca4dab98edaeb8bc661fad495a96e8b3890a` |

Архитектурная граница D01/D02/D03/D06/D07/D09/D11 и применимые R01–R12 сохранены в этом срезе: конкретная Core-композиция, явные roots, прежние guards/errors, неизменные входы и одна область записи. Закрытие эпиков этим не подтверждается. Workplace I/O, прямые/скопированные Core imports, миграция consumers, существующие интеграционные скрипты и native transitions остаются за primary. Main, документация, inventory и peer-продукты не изменялись; Git mutations, сеть, инфраструктура и вложенные агенты не использовались.
