# Alpha4: dev-поставка на устройство

## 2026-10-23 16:06 UTC — primary/orchestrator

Task: новая артефактная Work для явной установки alpha4 и приёмки функций.
Files analyzed: .pf/process-forge.yaml, .pf/AGENTS.md, alpha4 package/readiness,
native update/runtime contracts, current installed status and process provenance.
Status: context fresh/continue; assignment/capsule valid; orchestration.
Decisions: использовать квалифицированный payload, сохранить старые assets;
native update/restart разрешены текущим поручением пользователя; только own artifacts.
Risks: установлен alpha2; текущий MCP загружен до обновления; monitor cli_version
не является канонической версией Core. Первый admission с private paths отклонён
до создания Work; конфликт избыточного write_product устранён сужением grant.
Next: native baseline/plan, установка once, installed checks и отдельная MCP boundary.

2026-10-23T16:11:56.097389+00:00 | primary | Baseline captured: alpha2, all 1476 managed hashes match, no incomplete update; Workplace configs, unknown Core files, Runtime identity and foreign source preservation retained privately. Next: exact dev alias and native plan.

2026-10-23T16:13:13.261363+00:00 | primary | Distinct alpha4 dev alias prepared; ZIP byte-identical to qualified release, 1498 entries checked. Derived sidecar changes only filename. Next: native read-only plan.

2026-10-23T16:13:18.089191+00:00 | primary | Native dev update plan ready: 27 changed, 21 added, 1449 unchanged, zero local modifications/removals/blockers; no Workplace migration. Next: one apply with native backups.

2026-10-23T16:13:54.985727+00:00 | primary | Native apply returned success; original full receipt retained privately. Next: every installed hash, backups, config preservation, doctor/status/repair before any restart.

2026-10-23T16:14:54.384902+00:00 | primary | Installed alpha4 verified: all 1497 managed hashes match, configuration/unknown Core files and foreign source preserved, no incomplete update, nothing_to_repair. Next: conditional guarded Runtime restart and functional installed acceptance.

2026-10-23T16:20:07.847543+00:00 | primary | Installed acceptance payload prepared: 1497 installed files verified/copied; existing tests from exact qualified source, no working-copy test drift. Physical installed CLI batch probes retain original assertions.

2026-10-23T16:25:23.875457+00:00 | primary | Installed native smoke matrix completed; actual receipt retained. Next: physical installed CLI batch probe and live health.

2026-10-23T16:26:36.241258+00:00 | primary | Installed payload pytest completed; actual exit 0; see installed-pytest.json and retained raw logs. Next: remaining native/physical CLI coverage.

2026-10-23T16:27:01.020987+00:00 | primary | Operator explicitly approved ONE forced App Server restart after three guarded refusals. Fresh expanded read-only audit: complete, two registered projects, zero running workers, no issues. No standing force/MCP authority.

2026-10-23T16:27:08.399220+00:00 | primary | Exactly one approved native forced restart succeeded; new App Server owner ready. No repeated apply or forced restart. Next: final functional/health and actual MCP provenance checks.

2026-10-23T16:31:35.380231+00:00 | primary | Live installed context/search read-only checks captured with exact snapshot and index byte comparison; results in live-installed-checks.json. Existing MCP host reload remains separate.

2026-10-23T16:36:43.736036+00:00 | primary | Final scoped run/capsule doctors passed; installed 1497 hashes, Workplace config and foreign/source/alpha3/stable guards reverified. Remaining actual connected MCP reload and evidence Git delivery are tracked separately.

2026-10-23T16:42:13.234192+00:00 | primary | Portable checkpoint delivery: installation and installed/fixture acceptance complete; actual connected MCP reload remains required. No Work completion or host acceptance is claimed; exact continuation retained. Curating own artifacts only for dual-dev push.

## 2026-10-23T16:58:39.083551+00:00 — primary/session-close

Task: operator deferred MCP verification and requested saving all remaining artifacts for session close.
Files: session-close.md, session-close-retention.json, remaining postcommit receipts; private artifact inventory and assignment/capsule/run/snapshot copies.
Status: preservation only; continuation ready with no missing artifacts; native Work remains implementation/in_progress pending actual MCP acceptance.
Decisions: preserve all raw/private/failed evidence locally and sealed bytes unchanged; publish only portable receipts; no cleanup, update, restart, service stop, or further functional checks.
Next: resume exact alpha4-device-mcp-reconnect-20261023 after the operator reconnects MCP; do not repeat apply/force.
