# Строгий аудит предрелизных контрактов ProcessForge

- Assignment: `remediation-strict-contract-audit-20260730`
- Run: `pre-release-remediation-20260730`
- Role: `strict-contract-auditor`
- Date: 2026-07-30
- Режим: read-only assurance
- Решение: **FAIL — выпуск заблокирован**

## Результат

Принятый ADR
`.pf/adr/pre-release-remediation-no-compatibility-20260730.md:21-40`
требует одного канонического контракта, удаления legacy readers и aliases,
строгого `--dry-run XOR --apply`, reusable-template v2, структурного MCP
`auth` и release-manifest v2. Текущий публичный срез этим условиям не
соответствует.

Найдены не отдельные остаточные строки, а несколько действующих слоёв
совместимости:

1. схемы и smoke-тесты намеренно принимают superseded формы;
2. consumers продолжают читать legacy paths и неполные data shapes;
3. CLI публикует compatibility-команды, flat aliases и неявные режимы записи;
4. документация рекламирует оба варианта контракта;
5. release pack всё ещё использует manifest v1 и включает project `.pf`;
6. рабочая `.pf` и общий dogfooding workplace действительно содержат данные,
   которые необходимо мигрировать один раз до включения строгих readers.

## Метод и границы

По правилу проекта анализ начат через Serena. Symbol overview для
`tools/processforge.py` оказался недоступен (`Active languages: []`), поэтому
зафиксирован fallback: точечный Serena pattern search, затем `rg`, ограниченные
PowerShell line slices и read-only parser introspection. Продуктовые файлы не
изменялись.

Дополнительное фактическое подтверждение:

- `python tools/smoke_remediation_schema_inventory.py` — PASS и прямо сообщает,
  что reusable v1/v2 остаются валидными;
- `python tools/smoke_legacy_flat_process_layout_warning.py` — PASS, то есть
  legacy flat process реально загружается;
- `python tools/smoke_update_sites_schema.py` — PASS на legacy `url`;
- parser introspection показал, что `update candidates clear` и `release-pack`
  разбираются без `--apply`, с `dry_run=False`.

Проверка выполнялась на dirty worktree с активным независимым writer
`remediation-transactional-authoring-20260730`; его изменения не трогались.

## Release blockers

### B01. Release manifest v1 и project `.pf` всё ещё являются публичной поставкой

Доказательства:

- `tools/processforge.py:6560-6566` создаёт sidecar только из `name`, `version`,
  wall-clock `generated_at` и `files`; `schema_version: 2`, provenance,
  archive hash/size/count отсутствуют;
- `tools/processforge.py:6577-6604` не проверяет версию manifest и сверяет
  только список имён, но не hashes/sizes каждого ZIP member;
- `tools/validate-process-forge-checksums.py:26-28,49-63` продолжает включать
  `.pf/AGENTS.md`, `.pf/process-forge.yaml`, `.pf/hooks.yaml`;
- `tools/validate-process-forge-checksums.py:95-102` при отсутствии
  `checksums/processforge.sha256` читает legacy
  `.pf/artifacts/checksum-inventory.sha256`;
- `packaging/distribution-AGENTS.md` отсутствует;
- отдельной authoritative release-manifest v2 schema в `schemas/` нет.

Каноническая замена уже определена в release-integrity ADR: только manifest v2,
детерминированный publisher/provenance, `packaging/distribution-AGENTS.md` как
archive-root `AGENTS.md`, полное исключение `.pf/`, без v1 reader и без legacy
checksum fallback.

### B02. MCP продолжает писать и принимать `auth_ref`

Доказательства:

- `tools/processforge.py:21638-21656` записывает `auth_ref`;
- `tools/processforge.py:22871-22882` публикует `--auth-ref`;
- `schemas/mcp-definition.schema.json:13`,
  `schemas/mcp-registry.schema.json:26` принимают поле;
- `templates/mcp-definition.yaml:6` и
  `templates/registries/mcp.yaml:9` его создают;
- `docs/concepts/tool-mcp-registration.md:7` объявляет его рекомендуемым;
- `docs/concepts/workplace-init.md:71-72` смешивает `auth_ref`,
  `credential_ref` и `secret_ref`.

Канон из provider/runtime ADR:

```yaml
auth: null
```

или ровно одно из:

```yaml
auth:
  secret_ref: provider.github.token
```

```yaml
auth:
  env_ref: GITHUB_TOKEN
```

CLI: mutually exclusive `--secret-ref`, `--env-ref`, `--no-auth`.
Любое `auth_ref` должно быть schema/CLI error до записи proposal/event.

### B03. Reusable-template v1 остаётся полноценным публичным контрактом

Доказательства:

- `schemas/reusable-template.schema.json:6-32` содержит
  `oneOf(legacyV1, workplaceV2)`;
- `templates/reusable-template-template.yaml:1-16` сам является v1 fixture;
- `tools/processforge.py:21507-21508` превращает v1 в migration `WARN`;
- `tools/smoke_remediation_schema_inventory.py:138-166` требует, чтобы v1 был
  валиден.

Канон: только schema version 2 с `type: reusable_template`; v1 должен получать
FAIL без мутации. Public fixture и smoke необходимо перевести на v2/rejection.

### B04. Legacy platform layout всё ещё читается consumers

Строгая authoring preflight уже полезно отвергает legacy state
(`tools/processforge.py:22281-22310`), но consumer paths обходят этот барьер:

- `tools/processforge.py:3585-3595` сканирует project-root
  `platform-contracts/`, flat YAML и несколько вариантов layout;
- `tools/processforge.py:3619-3631` читает любой registry `path`, не требуя
  канонического root/id/path;
- `tools/processforge.py:21075-21086` doctor принимает unprefixed directory и
  `workplace/platforms/<id>/platform.yaml`;
- `tools/smoke_remediation_schema_inventory.py:192-200` использует
  non-canonical `platforms/joomla.cms/platform-contract.yaml`.

Канон: для workplace только
`platform-contracts/platform.<id>/platform-contract.yaml`; registry path,
stored id и package id проверяются вместе до чтения содержимого. Наличие old
path — invalid state, а не альтернативный candidate.

### B05. Legacy flat process layout загружается и имеет публичный migrator

Доказательства:

- `tools/processforge.py:11297-11371` включает три `legacy_flat` roots и
  загружает их с warning;
- `tools/processforge.py:13376-13378` doctor выдаёт WARN вместо FAIL;
- `tools/processforge.py:23303,23308` публикует origin/filter legacy;
- `tools/processforge.py:23327-23331` публикует `process-layout-migrate`;
- `tools/processforge.py:6224` включает smoke, утверждающий поддержку;
- `docs/concepts/process-directory-layout.md:13` и RU-аналог описывают fallback.

Канон: только `processes/core`, `processes/user`, `processes/custom` и
активированные official packs. Flat file — FAIL и zero mutation. Одноразовый
перенос internal fixtures не должен попадать в публичный CLI.

### B06. Deprecated context/ECP flow и checksumless capsules остаются рабочими

Доказательства:

- `tools/processforge.py:17949-17984,24024-24039` публикует
  `context-resolve` и `context-compile`;
- `tools/processforge.py:9890-9892` при отсутствии snapshot переключается на
  legacy `context-index` freshness;
- `tools/processforge.py:18003-18016` возвращает статус `legacy` для capsule
  без assignment checksum;
- `tools/processforge.py:16259-16265,17369-17373` разрешает такой capsule для
  запуска;
- `schemas/context-capsule.schema.json:11-22` не требует
  `assignment_checksum`;
- `schemas/execution-context-package.schema.json`,
  `templates/execution-context-package-template.yaml` и
  `processes/core/context-resolution.yaml:213,314-320` сохраняют ECP surface;
- `docs/concepts/execution-context-package.md:9-24`,
  `docs/validation/doctor-context.md:3-5` и другие docs описывают compatibility.

Канон: `project-context-refresh`, `project-context-check`,
`assignment-capsule`; checksum обязателен. Отсутствующий snapshot/capsule
contract — missing/FAIL, не fallback. ECP schema/template/command и legacy
context-index consumer удаляются; внутренние исторические файлы архивируются
или регенерируются.

### B07. Update-site contracts содержат несколько legacy spellings

Доказательства:

- `tools/processforge.py:18330-18350` сохраняет subject aliases
  `template`, `tool`, `mcp_server`, `package`;
- `tools/processforge.py:18352-18383` одновременно принимает `url`,
  `manifest_url`, `path`, `auth_ref`, `auth` и четыре синтаксиса env refs;
- `tools/processforge.py:18719-18725` взаимозаменяет `type` и `provider`;
- `tools/processforge.py:18757-18772` принимает `url/path` с migration WARN;
- `tools/processforge.py:18783-18788` рекомендует `auth_ref`;
- legacy update-site definitions дублируются в
  `package-manifest.schema.json`, `entity-update-sites.schema.json`,
  `tool-definition.schema.json`, `mcp-definition.schema.json`,
  `platform-contract.schema.json`, `reusable-template.schema.json`,
  `process-definition.schema.json`, `update-source-registry.schema.json` и
  `update-site-overrides.schema.json`;
- `docs/concepts/update-sites.md:30` и smoke закрепляют legacy `url`.

Канон следует заморозить один раз в `update-site.schema.json`: один provider
discriminator для каждого document type, `manifest_url` для JSON manifest
providers, структурный `auth`, один `env_ref` grammar, только канонические
subject types. Embedded copies должны ссылаться на один authoritative contract,
а не развиваться независимо.

### B08. Package-root registry можно обойти legacy fallback

Доказательства:

- `tools/processforge.py:2483-2490` считает missing/empty registry лишь WARN;
- `tools/processforge.py:7325-7337` возвращает
  `<workplace>/packages` fallback;
- `tools/processforge.py:7984-7987` создаёт этот fallback root при записи;
- `docs/concepts/path-resolution.md:33-36` обещает такую поддержку.

Канон: `registries/package-roots.yaml` обязателен для package resolution.
Missing/empty/unknown root — FAIL до proposal/event/directory writes.

### B09. Knowledge candidate reader синтезирует старые shapes

Доказательства:

- `schemas/knowledge-candidate.schema.json:34-36` наряду с `target` объявляет
  `target_package` и `target_type`;
- `tools/processforge.py:13493-13500` собирает canonical target из
  `target_type`, scalar `target`, `target_package`, `package`, `target_id`;
- `tools/processforge.py:11835-11836` принимает `candidate_id` вместо `id`.

Канон: обязательные `id` и `target: {type, id}`; legacy keys rejected before
queue/index/bundle writes.

### B10. Mutation mode contract системно не соблюдается

Главная причина находится в `tools/processforge.py:24051-24078`:

- XOR принудителен только для шести top-level commands;
- для остальных parser silently устанавливает `dry_run=True`, если `--apply`
  не передан;
- nested commands не могут быть корректно классифицированы по одному
  `args.command`.

Три класса нарушений:

1. оба flags есть, но отсутствие превращается в неявный dry-run:
   init/onboard, template/tool/MCP authoring, orchestration и другие;
2. есть только `--apply`, а `--dry-run` синтезируется скрыто:
   specialization, pack activation, run/task/iteration/handoff и knowledge hub;
3. есть только `--dry-run` или нет mode flags, а отсутствие реально пишет:
   `release-pack`, update rebuild/refresh/clear/stage/apply/rollback,
   notifications, agent ledger/session/lease, mode setters, supervisor ticks,
   context/capsule, chat/event и lifecycle commands.

Особенно опасны `tools/processforge.py:23038-23108`: update mutators публикуют
`--dry-run`, но не `--apply`; отсутствие flag означает mutation. Также
`clean --release` (`tools/processforge.py:22754-22757`) удаляет generated
release artifacts без mode pair.

Канон: registry команд по полному command path; каждый mutator имеет оба flags
и общий XOR preflight до любого mkdir/proposal/event/cache write. Read-only
commands не должны принимать mode flags «для symmetry».

### B11. Явные compatibility aliases остаются публичными

Ниже перечислены только подтверждённые aliases, а не вся harmless терминология:

- init: `workplace-init` назван alias
  (`tools/processforge.py:22523-22541`), `init-project`/`project-init` —
  aliases при наличии canonical `project-onboard`
  (`tools/processforge.py:22606-22640`);
- test aliases: `smoke-all` и `dogfood-test`
  (`tools/processforge.py:22723,22745`);
- update aliases: `update sources`, `update sources-list`
  (`tools/processforge.py:23023-23034`);
- flags: process authoring `--id`
  (`tools/processforge.py:23203-23217`), doctor `--project-root`
  (`23278-23284`), task `--read-file` (`23925`), platform ambiguous resource
  flags (`22994-22998`), specialization deprecated `--process`
  (`21827-21829,22916`);
- flat runtime/orchestration aliases:
  `runtime-driver-*` (`23404-23418`), `worker-run-*` (`23449-23462`),
  `supervisor-*` and `execution-inspector-*` (`23464-23530`),
  `orchestrator-plan-*`/`worker-launch-prompt-create` (`23572-23609`);
- session thin aliases: `session-heartbeat`, `session-end`, `session-status`
  (`23666-23684`).

Рекомендуемый public vocabulary: `workplace-init`, `project-onboard`, nested
`runtime-driver`, `worker-run`, `orchestrator-plan`,
`worker-launch-prompt`; для runtime observer — один nested
`execution-inspector <tick|run|status|stop>`. Для agent presence нужен один
session lifecycle vocabulary, без одновременно публикуемых agent/session
синонимов. `--process` в specialization следует заменить каноническим
`--applies-to-process`, так как само поле `applies_to_processes` поведенческое.

`orchestrator-shell-plan-*` не следует удалять механически: это отдельная
поведенческая surface с shell-agent policy, а не просто synonym generic apply.

### B12. Публичные schema/docs сохраняют deprecated contract names

- `schemas/process-definition.schema.json:35` допускает catalog role
  `legacy_alias`;
- `schemas/process-definition.schema.json:284` публикует deprecated
  `handoff_required`, хотя strict doctor уже его отвергает;
- `schemas/assignment.schema.json:55-61,103-112` и
  `schemas/context-capsule.schema.json:99-130` сохраняют string/object unions
  для `context_artifact` и `required_output`, добавленные как legacy input
  support;
- `docs/concepts/processforge-events.md:1-12` является compatibility pointer,
  при этом рядом остаются `schemas/processforge-event.schema.json` и
  `templates/processforge-event-template.json`; канон уже
  `docs/concepts/process-events.md` + `event-envelope.schema.json`;
- `tools/processforge.py:20421,20528,20985,21923` содержит четыре неиспользуемые
  `_legacy_command_*` реализации.

Deprecated lifecycle statuses (`draft`, `deprecated`, `archived`) сами по себе
не являются backward compatibility и сохраняются. Удалению подлежат только
alias role/field/read path.

## Внутренние одноразовые миграции

Эти данные не оправдывают runtime compatibility и должны быть преобразованы
отдельной контролируемой задачей:

1. **Общий workplace `D:\.agents\processforge-workplace`:**
   - 11 legacy platform contracts в `platforms/<id>/platform.yaml`;
   - registry содержит 11 paths этого вида и не имеет
     `platform-contract-roots.yaml`;
   - 8 reusable templates имеют `schema_version: 1` и не имеют canonical
     `type: reusable_template`;
   - 3 MCP registry entries и 3 historical proposals содержат `auth_ref: null`;
   - session-safe presence уже в порядке: 0 flat и 20 session records.
2. **Project `.pf`:**
   - 19 исторических `*.capsule.yaml` не содержат `assignment_checksum`;
   - `context-index.yaml` и `resolved-rules.yaml` всё ещё ссылаются на старые
     flat process paths, тогда как active `project-context.snapshot.yaml`
     использует `processes/core/...`;
   - snapshot `ctx-20260729-144103-0dda71.yaml` содержит 22 legacy platform
     references; два других проверенных snapshots таких ссылок не содержат;
   - 82 backfill YAML files содержат `handoff_required`;
   - 2 historical assignments содержат 8 plain-string `context_artifacts`.
3. Historical reports/ADRs не переписываются как доказательство прошлого, но
   должны иметь явную superseded metadata/index. В частности accepted
   schema-authority ADR всё ещё требует compatibility window и WARN
   (`:169-173,190-197,289-300,337-341`) и противоречит более позднему accepted
   no-compatibility ADR.

Порядок миграции: inventory + hashes, backup outside active roots, dry-run
conversion report, reviewed apply, strict doctors, regenerate current snapshot
и capsules, затем удалить/архивировать только неактивные legacy artifacts.
Public migration command в ZIP не создаётся.

## Ложные срабатывания, которые нужно сохранить

1. Проверка наличия legacy platform path с немедленным FAIL
   (`tools/processforge.py:22281-22310`) — это strict rejection, не reader.
2. Regression smoke
   `tools/smoke_remediation_platform_layout_strict.py` правильно доказывает
   rejection и zero mutation.
3. Launcher candidate fallback
   project override → workplace registry → `PROCESSFORGE_HOME`, заданный
   release-integrity ADR, — operational resilience. Он допустим, если каждый
   candidate полностью валидируется, stale candidate только диагностируется,
   а config не переписывается.
4. `fallback_if_no_director` — явная process error-routing policy, не data-shape
   compatibility.
5. `evolution_policy.compatibility` в process definitions описывает будущую
   semver policy после первого релиза; это не текущий legacy reader.
6. Lifecycle statuses `deprecated`/`archived` и тесты, проверяющие отсутствие
   старых artifacts, сохраняются.
7. `orchestrator-shell-plan-*` имеет отличное от generic apply поведение и не
   должен быть удалён как простой alias без отдельного API decision.
8. `legacy_webtolk_mapping` в official software pack — описательная миграционная
   таблица внешней предметной области, а не reader ProcessForge contract. Это
   не release blocker данного ADR; при желании её можно переименовать в
   `source_model_mapping`.

## План исправления: непересекающиеся задачи

Из-за монолитного `tools/processforge.py` code tasks ниже выполняются волнами с
единственным lease на этот файл. Параллельные writers для него запрещены.

### P0-1. Governance freeze

Scope: только `.pf/adr/**`, plan/index metadata.

- пометить schema-authority ADR как `superseded-in-part`;
- зафиксировать canonical command vocabulary и update-site document grammar;
- сделать no-compatibility ADR явным precedence source.

Exit: ни один accepted ADR не требует legacy WARN/read window.

### P0-2. Controlled dogfooding data cutover

Scope: только project `.pf/**` и
`D:\.agents\processforge-workplace/**`; никаких product files.

- мигрировать 11 platforms, 8 templates, MCP auth records;
- архивировать/regenerate checksumless capsules, stale context-index и old
  snapshots;
- обновить 82 backfill files и 8 assignment context items;
- сохранить before/after hashes и rollback package.

Exit: strict data inventory не находит legacy shapes/paths в active state.

### P0-3. Schema/template strictness

Scope: `schemas/**`, `templates/**`, `seeds/**`,
schema-only validator/smokes; без `tools/processforge.py`.

- reusable v2 only;
- MCP structural auth only;
- canonical update-site refs;
- required capsule checksum;
- canonical knowledge candidate;
- удалить `legacy_alias`, `handoff_required`, legacy assignment unions,
  duplicate processforge-event/ECP schemas;
- закрыть legacy properties через `additionalProperties: false` либо явный
  extension namespace.

Exit: negative fixtures для каждого legacy input дают schema FAIL.

### P0-4. Core consumer/CLI cutover

Scope: единолично `tools/processforge.py`, `tools/README.md` и связанные
code-level smokes.

- удалить platform/process/package/context/candidate legacy readers;
- удалить `_legacy_command_*`, compatibility commands и aliases;
- реализовать единый full-command-path mutation mode registry;
- заменить migration-WARN тесты на rejection + zero-mutation;
- оставить platform legacy existence checks как FAIL.

Exit: static scan не находит известных legacy markers; каждый mutator проходит
neither/both/dry-run/apply matrix.

### P0-5. Release integrity v2

Scope: после P0-4, с отдельным последовательным lease на
`tools/processforge.py`; дополнительно packaging/checksum/release schemas и
release smokes.

- реализовать v2 publisher/consumer;
- исключить `.pf`, удалить legacy checksum fallback;
- добавить distribution `AGENTS.md`, deterministic provenance и byte/hash/size
  verification.

Exit: v1 manifest rejected на всех readers; extracted archive проходит полный
release-archive-test и не содержит `.pf`.

### P1-1. Docs/process/packs canonicalization

Scope: `docs/**`, `processes/**`, `packs/**`, prompts/examples; параллельно
возможен только после freeze vocabulary.

- удалить compatibility pages/commands и migration WARN wording;
- обновить EN/RU command examples;
- убрать ECP artifact из context-resolution process;
- документировать только v2/auth/canonical layouts/mode XOR.

Exit: public text scan не находит deprecated/legacy acceptance.

### P1-2. Final independent assurance

Scope: read-only.

- strict static inventory;
- schema negative matrix;
- CLI alias absence and mutation zero-write matrix;
- shared workplace/project doctors;
- public release-test, extracted archive test, checksum and cleanliness.

Exit: все B01-B12 закрыты; release blocker list пуст.

## Итоговое решение

Release candidate сейчас принимать нельзя. Минимальный обязательный путь —
P0-1 → P0-2 → P0-3 → P0-4 → P0-5 → P1-1 → P1-2. Критично не «смягчать»
strict validation ради текущего workplace: рабочие данные уже измерены и могут
быть мигрированы один раз без публикации compatibility layer.
