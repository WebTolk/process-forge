# Изменения документального среза

- scope: только ревизия плана 02
- run: garage-revise-the-vision-alignment-plan-with-explicit-mcp-operability-ac

## Changed files

Новые plan.md, tasks.md и task-graph.json в этой директории, scope-and-design.md,
change-record.md и evidence 01–06; новый журнал и handoff r02.
На assurance/delivery/evolve сюда добавляются только документы проверок и
передачи, validation helper и evidence следующих стадий.
Штатные Assignment/capsule/Run/проекции создаёт PF.

## Change summary

Добавлены T08 восстановления MCP и T09 диагностики/логирования; расширены
T01 (общий контракт) и T06 (приёмка), обновлены порядок и зависимости.
Severity отделена от детализации, диагностические sinks от process journal.
MCP приёмка требует живого клиента, а не только CLI или запуска сервера.

Ревизия 01 и её evidence не редактировались. Продуктовый код, настройки
установленного MCP/хоста, глобальные skills и старые назначения не изменены.
Имя trace — профиль, не новый PSR-3 уровень. Реализация T08/T09 не выполнена.

## Handoff to assurance

Проверить десять ID, граф/DAG и порядок, локальные ссылки, восемь severity,
JSON evidence, ключевые safety acceptance, scope и сохранение предыдущей версии.
После проверки передать новую ревизию вместо старой, сохранив исторические
доказательства; product release not_applicable.
