# Handoff: plan revision -> operator / next coordinator

Objective:
Реализовать дополненный план PF с обязательной работоспособностью MCP и
диагностикой настраиваемой детализации.

Current status:
Новая ревизия плана: .pf/artifacts/vision-alignment-plan-20260925-r02/plan.md.
Текущая Work только документальная; авторитет её статуса —
garage-revise-the-vision-alignment-plan-with-explicit-mcp-operability-ac. T08/T09 не реализованы.

Input artifacts:
plan.md, tasks.md, task-graph.json и scope-and-design.md в директории r02;
неизменная исходная база и карточки ревизии 01.

Files changed:
Только документы r02, этот handoff, журнал и штатное состояние текущего PF Run.

Files not to touch:
Исторические runs/capsules/evidence, чужие dirty-файлы, installed Core/Workplace
и конфигурация хоста вне отдельной конкретно ограниченной работы.

Known issues:
Живой MCP возвращает stale для снимка, который source CLI считает fresh/ready.
Причина текущего расхождения ещё не установлена. T08 нельзя закрыть CLI workaround.

Required checks:
T08: воспроизведение, минимальный ремонт, регрессия и реальный клиент.
T09: severity/profile matrix, correlation, redaction/stdout, retention/overhead.
T06: обязательный повтор MCP acceptance после интеграции.

Next recommended action:
Рассмотреть ревизию 02; начинать с preflight и T08 по отдельному назначению,
не ожидая полного нового логгера. Прочие изменения — по указанному порядку.
