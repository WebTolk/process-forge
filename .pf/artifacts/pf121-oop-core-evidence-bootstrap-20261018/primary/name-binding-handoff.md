# Исправление областей видимости при интеграции Main

Native review attempt 1 завершился до запуска модели. Input capture вызвал
существующий hook admission и обнаружил hook_coordination_mode_invalid.
Исходный stderr/attempt сохранён. Причина — три ошибочные замены локальных
чтений project_mode внутри effective_project_coordination: глобальная функция
переносится в Core, локальная переменная должна остаться прежней.

Primary исправляет только эти чтения в своём Main scope и уточняет полный AST
proof с учётом symtable. Все семь worker products, три consumer migrations,
native algorithms/20 scenarios неизменны. Восемь успешных smoke receipts
сохраняются на прежних hashes; корректировка проверяется затронутыми существующими
coordination/hook сценариями и native input capture. Успешные сценарии не повторяем.

Предыдущий review Work с закреплёнными старыми hashes отменяется. Его capsule,
pins, failed attempt и исходные manifests/QA остаются историей. После исправления
создаётся отдельный review-final с актуальными final hashes и явным resolution,
без расширения product scope или инфраструктурных действий. Архитектура прежняя.
