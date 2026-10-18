# T08 — локальная поставка и решение о готовности

Result: PASS — test-stand installed Core and restarted host MCP accepted.
Public release: not_applicable; publication/push не запрошены и не выполнялись.

## Что поставлено

Исправление classifier provenance уже было в c810381 / source a180ad6.
Предыдущая сессия собрала чистый candidate, проверила source subset, архив
и extracted quick и применила ownership update core-update-20260925T143222Z.
27 файлов заменено, 12 добавлено, 0 удалено; Workplace migration not_applicable.
Текущая сессия подтвердила 954/954 owned hashes и реальную приёмку после restart.
Новая сборка/повторный apply не нужны и не выполняются.

Release-readiness-decided: локальная поставка принята по test-report.md.
Delivery-profile-run-or-skipped-with-reason: штатные release-pack,
release-archive-test --extracted-test quick и core-update plan/apply уже
выполнены и подтверждены archive-validation.md, implementation.md,
core-update-plan.json, core-update-apply.json; повторение не требуется.

## Установка, совместимость и откат

Установленная версия продолжает называться 1.1.0; identity определяется
commit/package/manifest hashes, а не одним VERSION. Архив SHA256:
324932d147aecb1ad7d1511735a7d69d4391c6220eb3dbc5e18e2d7ecbce6008.
Смена уже загруженного MCP выполнена операторским restart, подтверждена
новыми процессами и исправным поведением. Main snapshot не пересоздавался.

Backup сохраняется: D:/.agents/processforge/runtime/core-update/backups/
core-update-20260925T143222Z. Control manifests/plan и files определяют exact
rollback set. Last-apply journal не очищался. Откат не требуется; при будущей
ошибке сначала status/repair diagnostics по journal, без массовой замены Core.

После закрытия Run: архив/sidecar и runtime-before сохранить как durable local
delivery evidence; удалить только чистый detached T08 candidate и acceptance
scratch после архивации fixture evidence. Точные результаты — cleanup.json
и обновлённый handoff, без удаления чужих worktrees или пользовательского архива.

## Границы

Runtime ready/running, health degraded из-за чужого проекта — не общий health PASS.
Пустая выдача двух project-local ресурсов и unresolved template registry target
описаны в review-findings.md. Ни registry repair, ни чужие проекты не менялись.
T01 и T09 остаются отдельными Work; эта поставка их не реализует.
