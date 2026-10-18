# Handoff: T08 primary -> next session

Updated: 2026-09-25 18:36 +04:00. READY FOR OPERATOR SESSION RESTART.

## Objective

Продолжить поэтапное выполнение PF vision alignment plan r02. Сначала закончить T08:
работоспособность реально подключённого MCP, затем отдельной Work T01 и T09.
Не начинать повторную диагностику с нуля и не создавать дубль T08 Work.

## Current status

Installed update успешно применён и проверен. Current T08 stage **code-assurance**,
Run/Assignment in_progress. Implementation stage принят PF 2026-09-25T14:35:42Z.
Требуется операторский restart сессии, затем real-host MCP acceptance.
Не считать T08 завершённой; assurance-complete НЕ пройден.

## Read first / authoritative state

1. `.pf/AGENTS.md`, `.pf/process-forge.yaml`, этот handoff.
2. `pf.context(project_root="D:\\dev\\process-forge")` и `pf.work.state`.
3. `.pf/assignments/t08-mcp-operability-reproduce-current-source-versus-installed-mcp-freshn.yaml`
   и одноимённый immutable capsule в `.pf/contexts/assignment-capsules/`.
4. Артефакты `.pf/artifacts/t08-mcp-operability-20260925/`, особенно
   `scope.md`, `operator-authorization.md`, `investigation.md`, `architecture.md`.
5. План `.pf/artifacts/vision-alignment-plan-20260925-r02/plan.md`, `tasks.md`, `task-graph.json`.

Run: `garage-t08-mcp-operability-reproduce-current-source-versus-installed-mcp`.
Assignment: `t08-mcp-operability-reproduce-current-source-versus-installed-mcp-freshn`.
Process: `software-feature-development@1.1.0`; coordination single_agent — никаких subagents.
Fingerprint: `sha256:cc411028e9585dd8f56e07faa8997d9e7af1a39a801a0d8c0ca9c8c1e89dfd49`.
Pinned snapshot: `ctx-20260925-140110-0dbc7c`.

При недоступном MCP читать состояние source CLI:

```powershell
python -B bin/pf.py work-state --project-root . --run garage-t08-mcp-operability-reproduce-current-source-versus-installed-mcp --json
```

## Scope / permissions

Оператор разрешил обновлять установленный Core: эта машина — тестовый стенд.
Также предложил лично перезапустить сессии и попросил подробный handoff.
Installed Core `D:\.agents\processforge`; Workplace `D:\.agents\processforge-workplace`.
Это не project roots; не onboarding/init installed Core или Workplace.
Старый MCP не убивать. Перезапуск клиентской сессии — оператором после готовности.
Не менять host hooks/config, другие интеграции и чужие проекты. Никаких push/public releases.
Локальные конфликтующие owned files не перетирать через force без отдельного решения.

## Confirmed root cause

Source HEAD `a180ad624442d4fbe8ac1710073ef7d4c44babc4` уже содержит fix `c810381`.
Installed и source называют себя 1.1.0, но installed bytes старее.
Source CLI fresh/ready; installed CLI и подключённый MCP stale для одного snapshot.
Единственная причина installed CLI: `project classification changed`.
Classifiers одинаковы по SHA256; отличается только matched_rules[].source:
installed `software-web.yaml`, source/snapshot
`packs/official/software-development/project-classifiers/software-web.yaml`.
Подробные JSON: `classification-source.json`, `classification-installed-before.json`.
Новый source patch не нужен. Нельзя отключать freshness, переписывать snapshot старым Core
или подставлять выдуманную session, чтобы скрыть проблему.

MCP запущен из installed `tools/pf_runtime/mcp_server.py`, загружает Core относительно
своего пути и кеширует Python modules. Файловое обновление не меняет уже работающий MCP.
До обновления MCP PID15980 parent1604; Runtime PID14088 parent10944. Эти PID исторические:
никогда не посылать им сигналы без повторной exact identity проверки.

## Candidate / package / preflight

Clean detached candidate `.pf/tmp/t08-core-candidate-20260925` на a180ad6.
Archive `.pf/tmp/t08-core-package-20260925/processforge-1.1.0-a180ad6.zip`.
Sidecar одноимённый `.manifest.json`.
Archive SHA256 `324932d147aecb1ad7d1511735a7d69d4391c6220eb3dbc5e18e2d7ecbce6008`.
Sidecar SHA256 `8bf1220eaa1351fdb00307f1a3d5318e0e25583c6b8d77c0ab127e9975de60d7`.
Source tree `0b0ff44185d1ef4bc62e18a7f12678be4f160efc`, source dirty=false.
955 archive entries = 954 owned payload files + generated ownership manifest.
Plan: 27 changed, 12 added, 0 removed, 915 unchanged, 0 locally modified/missing.
Workplace migration not_applicable; no Workplace configuration writes planned.
`core-update-plan.json` содержит exact changed/added sets; unchanged omitted deliberately.

Source release-test subset PASS (7 checks, 59.649s), durable `source-test-report.json`:
classifier_distribution_parity, mcp_jsonrpc_validation, mcp_missing_session_diagnostics,
project_init_local_search_mcp, core_update_manifest, core_update_missing_owned,
core_update_migration_sources. Archive parity PASS; extracted quick PASS (162.90s,
finished 2026-09-25T14:30:10Z). Подробности archive-validation.md.
Это не полный public release-test и не разрешение публиковать релиз.

## Installed update / final verification

Apply 2026-09-25T14:32:22Z, id `core-update-20260925T143222Z`, status applied.
Exact output: `core-update-apply.json`; implementation record `implementation.md`.
954 installed owned files проверены по manifest: 0 mismatches; incomplete_update=false.
Doctor-workplace automatic post-update PASS; Workplace migration отсутствует.
Ничего не удалено. Backups всех 27 заменённых файлов проверены против old manifest: 0 mismatches.

Backup root: `D:\.agents\processforge\runtime\core-update\backups\core-update-20260925T143222Z`.
Внутри `files/` содержит old bytes; `control/old-manifest.json`, `control/new-manifest.json`,
`control/plan.json` определяют exact rollback set. Last apply journal:
`D:\.agents\processforge\runtime\core-update\last-apply.json`.
Не выполнять rollback просто ради restart. При реальной ошибке сначала core-update status/repair;
repair — диагностика, не автоматический откат. Не копировать backup поверх всего Core.

Installed processforge.py raw SHA256 `d3c100062981a351706c09f0808138edb6fe2ae7050a67a73fdbc306cb9a90be`;
mcp_server.py `404a7e00eb0d06097c616870ea03bd28200cf09d9c9f2a50ed3c5c8da4489bc1`.
Первичный checkout processforge.py имеет CRLF и raw 107786ac..., после нормализации LF
совпадает с released d3c100...; это объяснённое отличие, не новый defect (hash-normalization.json).

Installed context-check уже fresh/ready на том же snapshot и checksum, без refresh.
Installed-context-after.json содержит точный ответ; health warn не скрывать.
Четыре installed tests отдельными процессами PASS: classifier_distribution_parity,
mcp_jsonrpc_validation, mcp_missing_session_diagnostics, project_init_local_search_mcp.
Последний действительно запускает installed stdio MCP в изолированном fixture,
но это ещё НЕ acceptance текущего host-owned MCP.

Runtime штатно остановлен перед apply и поднят снова с port=0 / interval=2.0.
Новый PID2732, started_at 2026-09-25T14:32:50Z, endpoint http://127.0.0.1:51324.
Проверять эти значения заново, не полагаться на PID после restart.
Runtime running/status ready, health degraded WARN: scheduler сообщает, что отдельный
зарегистрированный `D:\Dev\plg-content-varreplace` не имеет `.pf/process-forge.yaml`.
Проект process-forge продолжает tick. Чужой проект не ремонтировать/инициализировать/удалять
из registry в рамках T08. Auth/protocol/singleton/handle/Ledger doctor checks PASS.
Operator log также содержит WinError10053 /event в 14:33:56Z; причина не исследована,
сохранена как отдельное наблюдение. Нельзя сообщать, что всё здоровье рабочего места зелёное.

Pre-update service metadata и журналы сохранены в
`.pf/tmp/t08-core-package-20260925/runtime-before/`; live logs не очищались.
Текущий MCP оставлен нетронутым и ещё может показывать stale до restart.

## Required checks after restart

1. Убедиться, что новый MCP реально загружен из обновлённого installed Core.
   `pf.context` на основном проекте: fresh, execution ready, тот же snapshot, process/resource
   semantics соответствуют source CLI. Не закрывать проблему одним initialize/healthcheck.
2. `pf.search` и `pf.resolve` разрешённого ресурса; отрицательная проверка чужого resource.
   Если индекс stale — сначала точная диагностика отдельного состояния, не отключать guard.
3. Sessionless Garage и bound-session authorization. Не использовать случайную реальную
   чужую session; отрицательные сценарии в изолированном fixture.
4. Изолированный fixture внутри `.pf/tmp/`: real host MCP `work.start -> state -> transition`
   до run_completed, с действительным evidence. Отдельное новое stdio connection должно
   продолжить тот же Work. Не путать успешный subprocess smoke с real-host acceptance.
5. Genuine stale/invalid requests/stdout clean проверяются регрессиями и фиксируются отдельно.
6. Пока всё выше не PASS, assurance-complete и T08 run_completed не объявлять.

## Remaining PF stages / evidence

Investigation, domain, architecture, implementation зарегистрированы через evidence 03/04/05/06.
Не редактировать уже hashed scope.md, investigation.md, domain.md, architecture.md, implementation.md.
Implementation уже completed; НЕ проходить его заново.
Code-assurance: review-findings, test-plan, test-cases, test-report; gate assurance-complete.
Release-delivery: delivery-report; gates release-readiness-decided,
delivery-profile-run-or-skipped-with-reason. Evolve: evolution-report, evolution-captured.
Процесс выбирает следующий этап сам; всегда outcome+evidence+notes, без next_stage.

```powershell
python -B bin/pf.py work-transition --project-root . --run garage-t08-mcp-operability-reproduce-current-source-versus-installed-mcp --outcome completed --evidence-file <new-evidence.json> --notes '<actual handoff>' --json
```

## Files not to touch / residual context

Checkout dev был dirty до T08. Сохранять старые планы, reference-projections, runs, capsules,
артефакты контекста и `задания.zip`. Не reset/clean широким списком. Product source не менялся.
Serena не умеет symbols здесь (Active languages: []); scoped rg/UTF-8 fallback documented.
Применимых development skills в user-authoritative D:\.agents\skills нет;
проектный PF software process определяет поток, не legacy global skills.
Временные candidate/package удержать до acceptance/rollback; удалять потом только exact paths.
Следующий план: T08 -> T01 -> T09 -> T02 -> T03 -> T04 -> T05 -> T06.
T07 privacy отдельно. T10 pf-server branding/terminal monitor — proposal.
Web только удалённый далеко позже, local web UI исключён.

## Next recommended action

Сейчас можно перезапустить сессию. После restart читать этот файл и продолжить тот же T08 Run
со стадии code-assurance. Первое действие — текущий pf.context, затем pf.work.state;
не стартовать новую T08 Work. Матрица фактических PASS/PENDING в test-matrix.md.

Короткое сообщение для новой сессии:
«Продолжай T08 по .pf/handoffs/t08-mcp-operability-20260925.md. Я перезапустил сессию;
проверь реальный MCP и заверши текущую Work через PF, затем переходи к T01.»
