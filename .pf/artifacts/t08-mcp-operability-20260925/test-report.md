# T08 — итоговый отчёт приёмки MCP

Дата: 2026-09-25. Result: **PASS for T08**.
Run: garage-t08-mcp-operability-reproduce-current-source-versus-installed-mcp.
Source: a180ad624442d4fbe8ac1710073ef7d4c44babc4; fix c810381 already included.

## Результаты по слоям

- Source: семь targeted checks PASS в предыдущей сессии; source-test-report.json.
- Archive: manifest/source/sidecar parity и extracted quick PASS; archive-validation.md.
- Installed: повторно проверены все 954 owned files, mismatches=0. Шесть targeted
  regressions после restart PASS, 85.924 s; installed-regressions-after-restart.json.
- Actual host MCP: context fresh на прежнем ctx-20260925-140110-0dbc7c, source и
  installed CLI execution ready; process pin/resources совпадают. Main T08 найдена
  на code-assurance без нового start и без повторного implementation.
- Actual host fixture: search/resolve PASS, cross-snapshot denial PASS, missing-session
  diagnostic PASS, start/state/invalid evidence/valid transition/run_completed PASS.
- Reconnect: новая installed stdio connection вернула continue_existing того же
  host-created Run на finish; stdout только JSON-RPC, notification без ответа,
  stderr пустой и exit=0. После этого именно host MCP завершил fixture.
- Genuine stale: изменён только manifest завершённого fixture; host search отказал
  snapshot_not_fresh. Возврат исходных bytes восстановил fresh без snapshot refresh.

Полная трассируемость C01–C14 находится в test-cases.md. Точный verdict опирается
на реальные MCP responses, отдельно сохранённый reconnect и installed regressions.

## Сохранность и ограничения

Main snapshot/checksum, original capsule и hashed scope/investigation/domain/
architecture/implementation не менялись. Конфигурация Workplace совпадает до/после.
Product source не менялся; чужие dirty-файлы, проекты и Ledger sessions не правились.

Runtime ready, health degraded из-за чужого project manifest; это предупреждение
сохраняется. Основной project-local corpus не входит в Workplace search catalogue;
его пустую выдачу не следует представлять как содержательный поиск по артефактам.
Неразрешимый старый template registry target также сохранён как наблюдение.
Подробности и направления follow-up: review-findings.md.

Browser verification: not_applicable, UI не менялся. Эта поставка — локальная
приёмка тестового installed Core, без public release/push. T01/T09 остаются
отдельными Works. Assurance-complete разрешён на основании приведённых PASS.
