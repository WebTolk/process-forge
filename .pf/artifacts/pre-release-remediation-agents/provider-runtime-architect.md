# Отчёт архитектора: provider, classifier и runtime-driver

- Assignment: `remediation-provider-runtime-design-20260730`
- Run: `pre-release-remediation-20260730`
- Findings: `PF-AUD-012`, `PF-AUD-013`, `PF-AUD-021`, `PF-AUD-022`
- Режим: read-only исследование product-кода; записаны только ADR и этот отчёт
- Результат: implementation-ready contract

## Итог

Подтверждены четыре класса несогласованностей:

1. MCP secret boundary сейчас эвристический и проверяет не то поле, которое
   хранит ссылку на авторизацию.
2. Публичные `tool-register` и `mcp-register` не исполняют одноимённые process
   contracts.
3. Classifier surface умеет читать данные, но не умеет безопасно создавать,
   регистрировать и диагностировать их.
4. Runtime-driver list и resolver выбирают разные same-id источники; doctor,
   validate-all и authoring отсутствуют.

Принятые решения закреплены в
`.pf/adr/pre-release-remediation-provider-runtime-design-20260730.md`.

## Метод и границы исследования

Сначала использована Serena, как требует проектная политика. Project onboarding
был выполнен, но symbol backend недоступен:

```text
Active languages: []
Cannot extract symbols from file tools/processforge.py
No language servers available in the manager
```

После этого применён разрешённый fallback: точечный Serena pattern search,
`rg` и построчные срезы PowerShell. Монолитный `tools/processforge.py` целиком
не считывался. Product-файлы не изменялись.

Исследованы:

- `tools/processforge.py`;
- восемь definition/registry schemas;
- `tool-register`, `mcp-register`, `runtime-driver-registry`;
- provider, classifier и runtime-driver templates/registries;
- schema validator mappings;
- существующие runtime/classifier smokes;
- EN-документация соответствующих surfaces;
- аудит, remediation plan и родительский schema-authority ADR.

## Точные symbol groups

### Secret и provider registration

| Symbol | Текущее поведение | Требуемое изменение |
|---|---|---|
| `SECRET_VALUE_PATTERNS` | Видит assignment-style secret и PEM, но не обычный `sk-*` | Оставить defense-in-depth, расширить token families |
| `contains_secret_value` | Возвращает результат только regex scan | Не считать это auth contract |
| `validate_resource_id` | Уже реализует строгую canonical id grammar | Использовать вместо `safe_id` |
| `write_resource_proposal` | Сразу пишет proposal | Вызывать только после полного input/registry preflight |
| `upsert_registry_entry` | Atomic replace после schema check будущего документа | До изменения валидировать также исходный registry, не «лечить» missing collection |
| `command_tool_register` | command scan, `safe_id`, proposal, registry, event, общий report | Двухфазный governed master |
| `command_mcp_register` | Проверяет command, но literal `args.auth_ref` сохраняет как есть | Структурный `auth`, двухфазный governed master |
| `command_doctor_workplace` | Registry parse/schema частично; нет provider semantics/readiness | Подключить общие tool/MCP doctor checks |
| `registry_ids` | Считает доступными id, package_id и capability без учёта status/health | Заменить provider-aware availability |

Current source snapshot evidence:

- `SECRET_VALUE_PATTERNS`: `tools/processforge.py:329-332`;
- `contains_secret_value`: `tools/processforge.py:665-666`;
- `command_tool_register`: `tools/processforge.py:20668-20701`;
- `command_mcp_register`: `tools/processforge.py:20704-20737`;
- parser surfaces: `tools/processforge.py:21389-21412`;
- `registry_ids`: `tools/processforge.py:3504-3515`.

Строки могут сдвинуться из-за параллельного remediation writer; symbol names
являются устойчивой ссылкой.

### Project classifier

| Symbol | Текущее поведение | Требуемое изменение |
|---|---|---|
| `project_classifier_registry_documents` | Собирает workplace/project/active-pack документы; часть ошибок молча пропускает | Возвращать provenance candidates и diagnostics |
| `project_classifier_paths` | Разворачивает активные paths без same-id resolution | Использовать общий selector |
| `project_classifier_condition_matches` | Generic exists matching | Сохранить |
| `project_classifier_rule_matches` | Generic all/any matching | Сохранить |
| `classify_project` | Последовательно применяет все загруженные документы | Получать только валидные selected definitions |

Public create/register/doctor symbols и parser entries отсутствуют.

### Runtime driver

| Symbol | Текущее поведение | Требуемое изменение |
|---|---|---|
| `runtime_driver_registry_paths` | Порядок distribution, workplace, project | Помечать scope; порядок сам по себе не является выбором |
| `runtime_driver_entries` | Invalid/missing registry превращается в пустой список | Возвращать blocking diagnostic |
| `runtime_driver_entry_path` | Разворачивает path без общего doctor result | Добавить containment и identity |
| `resolve_runtime_driver` | Возвращает первый same-id match, то есть distribution | Потреблять единый selected record |
| `runtime_driver_id_list` | Перезаписывает dict последним same-id match, то есть project | Потреблять тот же selected record |
| `validate_runtime_driver_document` | Semantic checks без authoritative JSON Schema | Schema first, затем semantics/readiness |
| `command_runtime_driver_list` | Печатает id/status/source из отдельной логики | Печатать shared provenance |
| `command_runtime_driver_validate` | Валидирует один resolved manifest | Shared resolution + schema; добавить validate-all |
| `command_runtime_driver_describe` | Показывает resolver result | Shared resolution |
| `runtime_driver_for_task` | Вызывает semantic-only validation | Блокировать execution на полном doctor result |

Public `create`, `register`, `doctor`, `validate-all` symbols отсутствуют.

## Secret reference contract

Рекомендован canonical MCP auth:

```yaml
auth: null
```

или ровно один reference:

```yaml
auth:
  secret_ref: provider.github.token
```

```yaml
auth:
  env_ref: GITHUB_TOKEN
```

`secret_ref` использует canonical resource id; `env_ref` — только имя
переменной окружения в верхнем регистре. CLI требует один из
`--secret-ref`, `--env-ref`, `--no-auth`.

Legacy `auth_ref`:

- читается один compatibility window;
- обязан выглядеть как reference id;
- literal-looking значение даёт `FAIL`;
- корректная legacy reference даёт migration `WARN`;
- `--auth-ref` становится deprecated alias `--secret-ref`;
- новые writers никогда не сохраняют `auth_ref`.

Причина выбора: regex не может доказать, что строка является ссылкой. Поэтому
reference type задаётся структурой поля, а secret scan остаётся дополнительным
барьером.

## Tool/MCP parity с процессами

Сейчас process definitions требуют:

- registration request;
- definition;
- validation report;
- review;
- blocking reviewed gate;
- healthcheck metadata;
- registered и healthcheck events.

CLI создаёт только proposal, registry entry, общий Markdown report и registered
event. Дополнительно `tool-definition`/`mcp-definition` объявлены как Markdown,
хотя их required templates — YAML. Это самостоятельное нарушение artifact
contract.

Выбран двухфазный master:

```text
dry-run -> полный план, без записи
prepare -> request + YAML definition + validation report, без registry
apply   -> proposal + SHA-bound PASS review + healthcheck -> registry last -> events
```

Review обязан быть внешним входом. Самоутверждение review той же мутационной
командой не считается выполнением blocking gate.

## Empty definition rules

Текущие schemas допускают пробельные значения:

- definition schemas используют `minLength: 1`, что принимает `"   "`;
- registry schemas для `name`, `capability`, `command`, `transport` не задают
  даже `minLength`;
- tool registry не требует `command`;
- MCP registry не требует `transport` и `command`;
- MCP `auth_ref` ничем не ограничен;
- configured MCP не имеет healthcheck contract.

Решение:

- id — `validate_resource_id`;
- name/capability/command/transport/healthcheck — `strip()` и обязательный
  non-whitespace;
- definition и embedded registry entry имеют одинаковые обязательные поля;
- configured provider требует explicit bounded healthcheck и успешный apply
  healthcheck;
- optional/missing/disabled никогда не считаются healthy или удовлетворяющими
  required capability.

## Classifier authoring contract

Добавить:

```text
project-classifier create
project-classifier register
project-classifier doctor
```

Canonical destination:

```text
<scope-root>/project-classifiers/<id>.yaml
```

Registry entry хранит canonical relative path. Doctor проверяет registry
parse/schema, duplicates, containment, manifest schema, id equality, rules и
status. Precedence:

```text
project > workplace > active package
```

Higher disabled — tombstone; same-scope duplicate — `FAIL`. Malformed registry
или registered document нельзя молча исключать из classification.

## Runtime-driver doctor contract

Добавить:

```text
runtime-driver create
runtime-driver register
runtime-driver doctor
runtime-driver validate-all
```

Один resolution record используется list/describe/validate/doctor/worker:

```text
project > workplace > distribution > builtin fallback
```

Higher disabled/missing блокирует fallback. Same-scope duplicate — `FAIL`.
Выбранный record содержит declared status, computed health, scope, registry,
manifest path, candidates и checks.

Порядок doctor:

1. registry YAML/schema;
2. duplicate/id/path containment;
3. manifest YAML/schema;
4. registry-manifest identity;
5. placeholders/reserved env;
6. kind semantics;
7. readiness.

Дополнительная найденная schema drift: runtime constant запрещает
`PF_AGENT_EXIT_PATH`, а `runtime-driver.schema.json` не включает его в
`propertyNames.not`. Schema должна быть синхронизирована с runtime.

## Test matrix

| Область | Positive | Negative | Mutation proof |
|---|---|---|---|
| MCP auth | secret_ref, env_ref, no-auth | raw tokens, both/neither refs, invalid env, literal legacy | registry/events unchanged |
| Provider fields | normalized nonblank values | whitespace-only fields, reserved/path-like id | no proposal before failed preflight |
| Review | SHA-bound `pass` | absent, stale hash, warn/skipped/fail, blocking issues | no registry/success event |
| Healthcheck | configured PASS | fail, timeout, blank command | no configured commit |
| Provider status | valid configured | optional/missing/disabled as required capability | unavailable never healthy |
| Classifier create/register | canonical manifest and entry | bad registry, traversal, id mismatch, empty rules | bytes unchanged |
| Classifier precedence | project/workplace/package | same-scope duplicate, disabled tombstone | deterministic selected provenance |
| Runtime create/register | manual and shell | blank executable, bad limits/env/placeholder | bytes unchanged |
| Runtime precedence | project/workplace/distribution/builtin | duplicate, higher missing/disabled | list equals executed provenance |
| Runtime doctor | all selected valid | corrupt registry/manifest, schema invalid | observational, bytes unchanged |

Отдельные smokes должны запускаться в source, public release, extracted archive
и consumer archive.

## Implementation scope и ownership

Рекомендуется один sole writer после освобождения текущей lease на
`tools/processforge.py`.

Product write scope:

- `tools/processforge.py`;
- `tools/validate-process-forge-schemas.py`;
- восемь provider/classifier/runtime definition/registry schemas;
- provider/classifier/runtime templates и четыре registry templates;
- runtime driver templates, затронутые schema tightening;
- `tool-register.yaml`, `mcp-register.yaml`,
  `runtime-driver-registry.yaml`;
- новый `project-classifier-authoring.yaml`;
- соответствующая EN/RU документация;
- dedicated remediation smokes;
- регистрация smokes в public release commands.

Отдельный reviewer запускается после freeze и не пишет product files.

## Риски и follow-up

- Provider healthcheck запускает локальную команду; runner обязан использовать
  bounded timeout, `shell=False`, redaction и не включать сырой output в events.
- Превращение `auth_ref` в structural `auth` требует явной migration command,
  но doctor не имеет права мигрировать автоматически.
- Capability values нельзя механически перевести на resource-id grammar:
  существующий capability vocabulary использует underscores.
- Direct unregistered runtime manifest path допустим для inspect/validate, но
  worker execution должен требовать explicit operator opt-in и полный doctor.
- `runtime-driver-registry.yaml` содержит дублированный
  `process-forge-core` в `required_packages`; это следует убрать в той же
  process-contract правке.

## Передача оркестратору

ADR готов для реализации. До начала provider/runtime slice нужно дождаться
освобождения текущего sole-writer scope `tools/processforge.py`. После
реализации обязателен независимый review по всем четырём findings и
byte-preservation negative tests.
