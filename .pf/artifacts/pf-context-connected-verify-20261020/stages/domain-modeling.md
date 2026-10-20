# Модель приёмки контекста

domain-notes: строка версии сама по себе не доказывает загрузку исправления.
Сопоставлены bytes трёх owner modules, путь запуска, родитель текущего host,
время старта MCP и неизменность snapshot. Старый MCP другого host не выбирался.

domain-model: project context freshness, resource freshness/search readiness,
Work execution readiness и policy_action — отдельные факты. В текущем наблюдении
проект fresh, CLI resources fresh, MCP search ready, exact Work valid/ready,
policy continue. Partial metadata coverage и stale derived reports сохранены
как диагностические пределы. Source, device installation и connected-host proof
связаны разными записями, а не смешаны в один результат теста.

domain-rules: immutable capsule и прежний snapshot не меняются; запрещённый ресурс
остаётся resource_not_in_work; native task-complete относится только к исторической
карточке согласованности. Source тесты зачтены только потому, что проверенные
module bytes совпадают; настоящие MCP ответы получены текущим подключением.

domain-rules-captured: вышеперечисленные границы отражены в evidence и критериях.
Handoff: architecture-plan определит артефакты, native closure и сохранение staging.
