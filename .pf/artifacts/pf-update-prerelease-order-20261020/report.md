# Минимальное исправление выбора prerelease обновлений

Исправлен только update selection: alpha1 → alpha2 → final, numeric/lexical
prerelease identifiers и игнорирование build metadata. Порядок соответствует
[SemVer 2.0.0, 9–11](https://semver.org/). Numeric/v-prefix shorthand и прежний
lexical fallback сохранены. Payloads, channels и общий ResourceVersionPolicy
не менялись; тест проверяет сохранение его прежних результатов.

Состав: maintenance/versions.py, focused pytest и одна собственная checksum row.
Неизменённые __init__/latest/normalize/candidate_id имеют прежний AST; форматирование
ограничено этим файлом. OOP54–55 и все выделенные чужие guards сохранены.

Проверки: исходный regression 10 FAIL/7 PASS; готовый кандидат 17 pytest PASS,
Ruff lint/format PASS двух файлов, existing update discovery smoke PASS.
Mypy изменённых типизированных методов __init__/_version_key/select — PASS по
точным AST source spans с доступными imports. Общий первый mypy выявил 264
транзитивные ошибки; проверка всего owner — 12 ранее существовавших ошибок
в latest/normalize и отсутствие pytest в type-check interpreter. Эти отказы
сохранены, не объявлены исправленными; error codes не отключались. Полный Core
typing не входит в минимальный freeze blocker fix.

Native lifecycle receipts, checks.json и candidate.json задают точные bytes.
Проверка готового diff выполнена основным агентом после реализации; новое
независимое ревью в этой Work не заявляется. Прежнее source review другого fix
не подменяет это изменение. Заморозка, суммарные source gates и публикация alpha1
следуют отдельной разрешённой release Work; этот fix не устанавливается на устройство.
