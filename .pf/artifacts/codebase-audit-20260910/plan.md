# План аудита

Основание: запрос пользователя от 2026-09-10. HEAD 901d0551773fe7a5b382b89ebe95b212b0747e83.

Цель: проверяемые ошибки Python, MCP и Runtime/хуков; отдельные задачи на устранение с границами, сложностью и критериями приёмки. Воркеры исполняют задания аудита и воспроизведения; продуктовый код не меняется.

Источник управления: новый carrier garage-audit-python-core-mcp-and-background-hooks-with-bounded-junior-sh создан source work-start. Connected MCP заблокирован stale, source project-context-check fresh/ready; инфраструктура не изменяется. Предыдущая context-collection диагностика остаётся самостоятельной незавершённой работой.

1. Зафиксировать исходное состояние и историю исправлений F01-F12.
2. Передать audit-core (M, Luna medium), audit-mcp (L, Luna high), audit-hooks (L, Luna high) независимые read-only области, каждому отдельные файлы доказательств.
3. Оркестратор независимо проверяет реальные входы и воспроизведения, запускает релевантные существующие проверки, отвергает ложные срабатывания.
4. Итоговый отчёт, изолированный backlog задач, handoff, проверка неизменности исходников и PF doctors.

Serena symbol extraction unavailable: active languages empty. Read/pattern search available; shell fallback for symbols. No fixed platform/toolchain in project profile. Full release qualification is outside this audit.
