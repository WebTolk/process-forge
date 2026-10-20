# Ограниченная реализация version precedence

architecture: существующий UpdateVersionSelectionPolicy получает приватный key,
переиспользующий numeric/lexical распознавание ResourceVersionPolicy. В numeric
ключ добавляются release flag и tagged numeric/lexical prerelease identifiers;
build suffix исключается. select сравнивает такие ключи только когда обе версии
numeric; иначе прежний is_newer сохраняет предупреждение и lexical сравнение.

implementation-plan: один owner, focused pytest через публичный select и normalize,
pytest/Ruff/mypy и два имеющихся update/resource smokes. Изменяется одна inventory
row owner файла; старые dirty inventory rows сохраняются. После готовности —
сверка diff и guards; отдельный commit/readback двух dev, затем freeze release.

decision-log: общую ResourceVersionPolicy не расширять; новые dependencies,
global version abstraction и рефакторинг не нужны. Публикация alpha разрешена
новым поручением, но остаётся вне capsule этой Work и пойдёт следующим результатом.
architecture-plan-ready: scope достаточен, поведение и проверки ограничены blocker fix.
Handoff: implementation добавит tests и минимальный key, без OOP продолжения.
