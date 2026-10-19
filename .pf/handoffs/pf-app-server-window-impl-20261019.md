# Handoff: assurance worker -> primary executor, R1

Дата: 2026-10-19. Это неизменяемая передача области R1, не финальное закрытие задачи.
Итог основной Work после повторного review: см. ../artifacts/pf-app-server-window-impl-20261019/primary/closeout.md.

Objective: добавить постоянную проверку исправления R1 в tools/smoke_server_console.py.
Current status: original assurance worker completed/collected, Ledger checked out;
primary выполняет коррекцию. Все прежние результаты остаются историческими.
Input artifacts: ../artifacts/pf-app-server-window-impl-20261019/primary/R1-handoff.md,
../artifacts/pf-app-server-window-impl-20261019/assurance/report.md.
Files changed: только tools/smoke_server_console.py в новой тестовой Work;
console.py отдельно остаётся у исходной primary Work.
Files not to touch: чужие product files, конфигурация PF, Runtime/MCP/Task Scheduler.
Known issues: header write/flush может выбросить OSError до runtime.serve.
Required checks: failure before fix, write/flush service-continuity after fix,
затронутые canonical smokes, новое hash/public freeze и independent re-review.
Next recommended action: admit explicit test-only successor, primary fixes own
console.py, тот же reviewer проверяет R1 patch. Коммиты/push только после review.
