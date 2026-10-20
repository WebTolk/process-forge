# Оркестрация: согласованность контекста CLI/MCP

Дата: 2026-10-20. Роль: основной агент.
Исходная карточка: pf-cli-mcp-context-consistency-20261019.
Новая Work: garage-pf-context-parity-20261020-diagnose-and-fix-pf-cli-mcp-context-co; assignment pf-context-parity-20261020-diagnose-and-fix-pf-cli-mcp-context-consisten.
Capsule: pf-context-parity-20261020-diagnose-and-fix-pf-cli-mcp-context-consisten-capsule; sha256:00344bd0fed9d8e68f3cc4049a4e0125d5411dc21fe92684f9c4c2910755ee1e.

## task-record
Поручение пользователя: устранить расхождение CLI/MCP по процессу PF с разрешёнными знаниями Python, затем дать оценку альфа-релиза сегодняшних изменений.
Единица результата: одно исправление общей проверки контекста с необходимой диагностикой и регрессиями, независимым ревью и доставкой исходников в обе dev.
Публикация alpha tag/assets/channel не входит в это поручение оценки готовности.

## execution-context-summary
Проект process-forge; выбранный процесс software-feature-development 1.2.1, pin valid, immutable capsule valid/ready; действия read/write_artifact/write_product ограничены капсулой.
Снимок ctx-20261020-072238-da5df2; source CLI fresh/ready/continue.
Установленный CLI и подключённый MCP stale: source changed: official-pack-processforge-official-software-development-package.
Карточка legacy planning-only не расширяется. Создана новая ограниченная Work; OOP54-55, сторонние изменения и службы вне записи.
Serena активна и применена для картирования owners. Источники Python выбранные PF; work-resolve подтвердил доступ к docs.python, docs.python-practices, docs.python-peps.
Валидация двух начальных scope-intent отклонена до создания Work; неверная ссылка predecessor_handoff и resource ids в поле required_sources исправлены в bootstrap-входе. Исторические rejected JSON сохранены в scratch.

## lifecycle-mode-decision
Режим bug_fix с полной последовательностью существующих стадий.
Основной агент ведёт исследование/проектирование/реализацию и проверки. Независимый reviewer получает отдельную ограниченную Work после готовности реализации.
Доставка исходников обязательна; оценка alpha учитывает установку и connected-host отдельно.
Разрешения на инфраструктурную установку/reload не выводятся из этого документа.

## context-ready
Нативные work-state, assignment и capsule прочитаны; project/run/assignment/context/checksum совпали; grants и selected_resource_ids проверены.
Source CLI даёт действующий fresh контекст и обеспечивает файловый процесс; MCP-расхождение является предметом этой Work, а не основанием подменить контекст refresh/restart.

