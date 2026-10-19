# Изменения и граница поставки планирования

Status: ready_for_review
Date: 2026-10-19

## Changed files / change summary

Результат — документы и доказательства под
`.pf/artifacts/pf-app-server-window-plan-20261019/`, выделенный журнал
`.pf/logs/pf-app-server-window-plan-20261019.md` и handoff
`.pf/handoffs/pf-app-server-window-plan-20261019.md`.

ProcessForge штатно создал отдельные scoped Run, Assignment, immutable capsule
и зафиксировал stage transitions. До admission по разрешению пользователя
обновлён устаревший project-context snapshot. Исходная legacy-карточка
`pf-app-server-window-ux-20261019` сохраняется открытой; её scope/история
не переписаны.

Продуктовая реализация: **not_applicable** в этой Work.
Причина: пользователь поручил только планирование; capsule запрещает
`write_product` и содержит `code_changes_allowed: false`.
Выбор Textual и обсуждение GUI запуска этого ограничения не отменили.
Evidence: `control.md`, окончательные пользовательские решения в `plan-v2.md`,
`product-baseline.json`, `product-preservation.json`.

Нет продуктового patch, установки зависимости, изменения scheduled task,
запуска/остановки/перезапуска Runtime/MCP/monitor, установки на устройство
или внешней публикации. Source smoke и реальная GUI/logon проверка
не выполнялись; это будущая приёмка реализации.

## Delivery decision

Product release/build/package/install: **not_applicable**.
Причина: поставляется план для review, исполняемый кандидат не создавался.
Evidence: `plan-v2.md`, `review.md`, локальные документы и их проверки.

Existing product delivery profiles не запускаются для проверки этих
Markdown/JSON артефактов. Самостоятельная локальная фиксация собственных
плановых материалов следует правилам проекта и не является публикацией
продукта. Чужое dirty/staged состояние не включается в неё.

## Evolution capture

Будущая идея пользователя о списке проектов и просмотре подробностей
сохранена в `future-ideas.md`. Она не реализована, не включена в первую
версию панели, не получила нового расписания/worker или дублирующей задачи.

Для инструкций установки требуется различать отсутствие консоли через
pythonw и минимизацию видимого окна. Это предложение будущей правки
инструкции, а не уже выполненная правка публичной документации.

Правила, глобальные skills, память агента, process definitions и знания
Workplace не меняются. Licensing note относится к выбранной библиотеке;
проверка конкретного dependency lock и готовой поставки остаётся будущей.

Handoff: план готов для review; реализация требует отдельной Work с
продуктовыми scopes, обязательными архитектурными входами и новой проверкой
актуального контекста. Терминальную planning Work не возобновлять для кода.
