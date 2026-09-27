# Handoff: T08 accepted -> T01

Updated: 2026-09-25 22:17 +04:00. T08 COMPLETED; restart acceptance PASS.

## Objective and current status

T08 завершена через реально подключённый MCP. Последовательность
code-assurance -> release-delivery -> evolve пройдена; ответ main-completed.json:
`action: run_completed`, Run completed, Assignment done, completion complete.
Все 9 стадий и хеши их evidence проверены. Source run-doctor: 21 PASS, exit 0.
Новая T08 Work не создавалась; implementation не повторялся.

Run: garage-t08-mcp-operability-reproduce-current-source-versus-installed-mcp.
Assignment: t08-mcp-operability-reproduce-current-source-versus-installed-mcp-freshn.
Process: software-feature-development@1.1.0; coordination single_agent.
Pin: sha256:cc411028e9585dd8f56e07faa8997d9e7af1a39a801a0d8c0ca9c8c1e89dfd49.
Main snapshot: ctx-20260925-140110-0dbc7c — НЕ пересоздавался.
Source HEAD: a180ad624442d4fbe8ac1710073ef7d4c44babc4; product source в T08 не менялся.

## Accepted proof

Все материалы: .pf/artifacts/t08-mcp-operability-20260925/.
- test-report.md, test-cases.md, review-findings.md — итоговый verdict и границы.
- host-context-after-restart.json + context-cli-parity-after-restart.json:
  actual host fresh, source/installed CLI fresh and execution ready,
  same snapshot/checksum; process pin/resources совпали.
- host-process-identity.json: новый actual Python MCP PID5044 через launcher18788,
  установленный tools/pf_runtime/mcp_server.py. PID исторические после проверки.
- fixture-search-positive.json / fixture-resolve-positive.json:
  existing docs.api.gitverse:root найден и разрешён через host MCP.
- main-resolve-denied.json: тот же resource запрещён в основном проекте.
- host-missing-session.json: Forge-only session_context возвращает missing_session.
- fixture-work-start/state, fixture-invalid-evidence, fixture-transition-verify,
  fixture-completed: actual host стартовал, отклонил missing evidence без мутации,
  принял действительные evidence и завершил изолированный двухэтапный Run.
- reconnect-proof.json: отдельная новая installed stdio connection вернула
  continue_existing того же Run/Assignment на finish, принятый input сохранён;
  stdout только JSON-RPC, notification silent, empty stderr, EOF exit 0.
- fixture-stale-search.json: реальный drift manifest блокируется snapshot_not_fresh;
  возврат исходных bytes вернул fresh без refresh — fixture-context-restored.json.
- installed-regressions-after-restart.json: шесть тестов PASS, 85.924 s.
- final-verification.json: все 954 owned hashes совпадают, исходные evidence/capsule
  и Workplace configuration не изменены. Runtime ready/running, health degraded.
- closeout-proof.json: main/fixture completion consistency, doctors и fixture archive.
- evidence/07.json, 08.json, 09.json и main-*-transition/completed.json: PF transitions.

## Residual observations / do not overclaim

Основные два project-local ресурса не входят в physical Workplace catalogue;
main search даёт 0, хотя global readiness ready/85 docs. Это НЕ доказанный поиск
по артефактам проекта. Диагностика: search-catalogue-diagnosis.json. Учесть T01/T02.
Первый выбранный fixture template php.class-doc-block имеет unresolved registry
path; это сохранено как наблюдение, registry не ремонтировался.
Runtime health degraded из-за другого проекта plg-content-varreplace без manifest;
его не правили. Старый /event WinError10053 отдельно не исследован.
Public release не квалифицирован, push/publication не выполнялись.

## Package, rollback and cleanup

Чистый T08 candidate удалён штатным git worktree remove, без force.
Fixture evidence сохранено в fixture-evidence.zip (29 entries, testzip PASS),
SHA256 6a4317ea6f2b5e82df8cf1fecba1b5bbec17be01561be7d0322612bec67ebcea;
после этого удалён только exact fixture scratch. cleanup.json — точный журнал.

Пакет/sidecar/runtime-before перенесены из временного каталога в durable:
.pf/artifacts/t08-mcp-operability-20260925/delivery-package/.
Archive processforge-1.1.0-a180ad6.zip, SHA256
324932d147aecb1ad7d1511735a7d69d4391c6220eb3dbc5e18e2d7ecbce6008.
Installed backup не удалён:
D:/.agents/processforge/runtime/core-update/backups/core-update-20260925T143222Z.
Control old/new manifests и plan определяют exact rollback set. Last-apply сохранён.
Нет оснований для повторного apply/rollback/restart.
Исторический полный handoff до restart: handoff-before-host-acceptance.md.

## Next recommended action / current operator authorization

Оператор 2026-09-25 после приёмки T08 прямо поручил:
«Работай по плану в автоматическом режиме. После проверки и приемки одного этапа
начинай следущий. Ты в режиме AFK. Я завтра проверю работу.»
Это более новое поручение, чем ограничение последнего отчёта текущей T08.

Начать T01 отдельной Work через pf.work.start, прочитать assignment/capsule,
сначала scope/investigation/domain/architecture, затем implementation/assurance.
Действует план r02: T01 -> T09 -> T02 -> T03 -> T04 -> T05 -> T06.
T07 — отдельное последующее проектирование, T10 — proposal; local web UI исключён.
Не менять защищённые r01/r02 plans и evidence завершённой T08. Прогресс новых Works
фиксировать отдельно. Старые dirty-файлы, прошлые runs/capsules и задания.zip сохранить.
PF single_agent запрещает subagents. Serena/IDE MCP недоступны; scoped UTF-8 fallback.
