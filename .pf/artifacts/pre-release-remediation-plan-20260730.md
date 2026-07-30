# План исправления предрелизных дефектов ProcessForge

- Связанная задача:
  `.pf/assignments/pre-release-remediation-implementation-20260730.yaml`
- Run: `pre-release-remediation-20260730`
- Источник: `.pf/artifacts/pre-release-product-audit-20260730.md`
- Статус: `open`, реализация не начата
- Цель: закрыть все Critical и High findings, вернуть достоверность мастеров,
  doctors и release gates, затем собрать прослеживаемый release candidate.

## 1. Принципы выполнения

1. Сначала фиксируются контракты, затем код.
2. Для каждого дефекта сначала создаётся отрицательный regression test,
   воспроизводящий подтверждённое поведение.
3. `tools/processforge.py` имеет только одного writer одновременно.
4. Параллельно допустимы независимые исследования, тестовые fixtures, docs и
   review, но не конкурирующие изменения монолитного CLI.
5. Creator считается исправленным только если выполняется postcondition его
   собственного doctor и authoritative schema.
6. Failed operation не должна оставлять active, available или частично
   committed entity.
7. Public release PASS не заменяет project-local dogfooding.
8. Release ZIP собирается последним, из чистого зафиксированного Git state.
9. Удалять неудобные dogfooding tests для получения зелёного release нельзя:
   их нужно исправить или оформить явный waiver.
10. Commit/push и публикация не входят в автоматическое продолжение задачи без
    отдельного подтверждения владельца.

## 2. Definition of Done

Задача может перейти в `done`, только если:

- PF-AUD-001—PF-AUD-018 имеют disposition `fixed` и подтверждённый test id;
- PF-AUD-019—PF-AUD-028 исправлены либо имеют review-approved waiver с
  владельцем и сроком;
- traversal на Windows и POSIX separators блокируется до любой записи;
- creators, doctors и schemas используют единый контракт;
- process version collision по умолчанию завершается отказом;
- unknown/inactive process является blocking error во всех lifecycle/context
  поверхностях;
- intentional resource parity FAIL и intentional public gate FAIL дают
  ненулевой exit code;
- tampered ZIP не проходит consumer-mode verification;
- linked launcher восстанавливается после relocation через объявленный
  precedence contract;
- project-local dogfooding зелёный либо содержит только оформленные waivers;
- source public release test, release-pack и full extracted archive test PASS;
- итоговый manifest содержит достаточную provenance для привязки к source
  state;
- независимый review не содержит незакрытых Critical/High.

## 3. Фаза 0 — зафиксировать authoritative contracts

### Цель

Не кодировать очередное расхождение между schemas, manifests и CLI.

### Решения

1. ADR по id grammar:
   - разрешены ли dotted ids у knowledge packages и templates;
   - единая нормализация и запрет path separators, `.`/`..`, absolute/UNC;
   - containment после filesystem resolution.
2. ADR по manifest authority:
   - один schema для authored reusable template;
   - допустимый enum package `kind`;
   - обязательные поля platform registry;
   - migration для official/seeds manifests.
3. Doctor contract:
   - YAML parse;
   - JSON Schema;
   - semantic references;
   - path containment/public safety;
   - health/readiness;
   - единая exit policy для FAIL/WARN.
4. Transaction contract:
   - preflight;
   - staging;
   - validation/review;
   - atomic commit;
   - rollback;
   - event order.
5. Release integrity contract:
   - consumer verification без source checkout;
   - checksum surface;
   - commit/tree/dirty provenance;
   - значение synthetic `public-gate`.
6. Launcher precedence:
   - explicit valid override;
   - workplace registry;
   - `PROCESSFORGE_HOME`;
   - диагностика stale override.

### Артефакт

`.pf/adr/pre-release-remediation-schema-authority-20260730.md`.

### Exit gate

ADR одобрен до изменения schemas/generators/doctors.

## 4. Фаза 1 — закрыть security и filesystem boundaries

### Findings

PF-AUD-001, PF-AUD-002, часть PF-AUD-012.

### Изменения

1. Ввести общий primitive:
   - canonical resource id validation;
   - reject separators, drive/UNC, dot segments и encoded traversal;
   - resolve target;
   - containment against declared root;
   - fail before proposal/event/registry/file write.
2. Применить его ко всем package/specialization entry points, включая hub
   build/release и read/doctor resolvers.
3. Ввести строгую grammar для `auth_ref`; literal-token detection выполнять до
   записи proposal и registry.
4. Не использовать `safe_id` как неявную security boundary.

### Tests

- `..\..`, `../../`, mixed separators;
- absolute drive, UNC, rooted path;
- trailing dot/space Windows cases;
- canonical valid dotted/dashed ids по принятому ADR;
- существующий файл за root плюс `--force`;
- literal `sk-*`, bearer/token/password forms;
- доказательство отсутствия новых файлов/events/registry mutations при отказе.

### Exit gate

Все traversal/secret tests FAIL до исправления и PASS после; temp root остаётся
неизменным.

## 5. Фаза 2 — синхронизировать schemas, generators и doctors

### Findings

PF-AUD-005, PF-AUD-006, часть PF-AUD-021/022/027.

### Изменения

1. Обновить authoritative schemas по ADR.
2. Мигрировать:
   - official knowledge manifests;
   - seeds;
   - template examples;
   - platform registry templates.
3. Подключить общий schema-validation helper к:
   - knowledge-package doctor;
   - template doctor;
   - platform doctor;
   - specialization doctor;
   - process doctor;
   - project/workplace doctors;
   - provider/runtime-driver validators.
4. Запретить synthetic fallback manifest после YAML parse error.
5. Запретить `upsert_registry_entry` сбрасывать invalid registry; возвращать
   blocking error, сохранять исходный файл.
6. Расширить `validate-process-forge-schemas.py` на official/seeds knowledge
   manifests и все generated registry/template contracts.
7. Добавить completeness checks для `process-packs`, classifiers,
   specializations и runtime drivers.

### Tests

- invalid YAML;
- missing required key;
- bad enum/id;
- unknown forbidden property;
- corrupt registry followed by register attempt;
- missing `process-packs.yaml`;
- 100% official/seeds manifest validation;
- normal valid generated entities как positive controls.

### Exit gate

Каждый generated artifact проходит schema; каждый intentional invalid fixture
даёт doctor FAIL; ни один corrupt registry не перезаписан.

## 6. Фаза 3 — сделать authoring transactional

### Findings

PF-AUD-010, PF-AUD-011, PF-AUD-019, часть PF-AUD-020.

### Изменения

1. Общий authoring transaction:
   - вычислить полный write set;
   - preflight collisions и parent types;
   - staging в том же filesystem;
   - schema/doctor/review на staged state;
   - atomic replace/rename;
   - registry последним;
   - rollback при исключении.
2. Failed platform:
   - не регистрировать `available`;
   - не публиковать `authoring.completed`;
   - корректный failed event и report.
3. Knowledge manifest/index обновлять одной транзакцией.
4. Объединить или явно развести layouts `platform-create` и
   `platform-contract-install`; same-id collision не должен молча shadow
   существующую сущность.
5. Process-create должен проверять initialized root до создания authoring
   session/event.
6. Dry-run обязан перечислять полный apply write set.

### Tests

- искусственная ошибка на каждом шаге транзакции;
- file вместо expected directory;
- registry write failure;
- duplicate entity;
- failed doctor/review;
- сравнение дерева и registry до/после отказа;
- dry-run/apply path parity.

### Exit gate

После любого injected failure состояние совпадает с исходным либо содержит
только явно маркированный recoverable draft, никогда `available`.

## 7. Фаза 4 — восстановить process и lifecycle invariants

### Findings

PF-AUD-007, PF-AUD-008, PF-AUD-009, PF-AUD-017, PF-AUD-020.

### Изменения

1. Process immutability:
   - collision same id/version — FAIL;
   - изменения только через `process-version-upgrade`;
   - explicit override требует reason и audit trail.
2. `run-create`/`task-create`:
   - process обязан разрешаться и быть active;
   - initial terminal statuses проходят terminal invariant validation;
   - creator запускает те же postconditions, что doctor.
3. Context resolver:
   - unknown/inactive process становится blocking conflict;
   - пустой route не может иметь `status: resolved`;
   - snapshot build наследует тот же результат.
4. Strict catalog collision:
   - включить collision в report checks/summary/exit;
   - разрешать только declarative override с reason.
5. `iteration-complete`:
   - только terminal statuses;
   - согласованные status/completed_at/event.

### Tests

- duplicate same-version process;
- approved version upgrade;
- missing/inactive process для context/run/task/snapshot;
- terminal run without summary/handoff;
- strict duplicate без/с override reason;
- каждый допустимый и недопустимый iteration status.

### Exit gate

Ни одна lifecycle entity не может быть создана в состоянии, которое её doctor
сразу отвергает.

## 8. Фаза 5 — привести provider, classifier и runtime-driver surfaces к контракту

### Findings

PF-AUD-012, PF-AUD-013, PF-AUD-021, PF-AUD-022.

### Изменения

1. Разделить low-level registry mutation и governed master либо реализовать
   process contracts полностью.
2. Для `tool-register`/`mcp-register`:
   - nonblank normalized id/capability/command;
   - auth reference validation;
   - declared artifacts и review;
   - blocking reviewed gate;
   - healthcheck и корректные events;
   - doctor schema/semantic/readiness checks.
3. Добавить документированный classifier authoring/register/doctor путь либо
   явный import-only contract с validator.
4. Для runtime drivers:
   - create/register или документированный manual install flow;
   - validate-all;
   - schema-required fields;
   - единая precedence у list и resolver;
   - same-id override policy.

### Tests

- whitespace-only provider fields;
- missing executable/capability;
- failed healthcheck;
- secret literal;
- reviewed/unreviewed registration;
- malformed/missing classifier registry;
- runtime driver same-id precedence;
- list provenance совпадает с resolved driver.

### Exit gate

Неработоспособный provider/driver не может получить healthy/available PASS.

## 9. Фаза 6 — исправить release gates, integrity и linked installation

### Findings

PF-AUD-003, PF-AUD-004, PF-AUD-014—PF-AUD-016, PF-AUD-018,
PF-AUD-023—PF-AUD-025.

### Изменения

1. `authoring-parity-check-all` возвращает aggregate result.
2. Определить `public-gate` как реальную группу public commands; `--only` и
   `--skip` должны выбирать группу предсказуемо.
3. Consumer archive validator:
   - вычисляет hashes ZIP entries;
   - сверяет их с manifest без `--root`;
   - проверяет duplicate/casefold/path safety;
   - tamper всегда FAIL.
4. Покрыть checksum inventory всей shipped surface либо явно оформить
   self-checking design.
5. Добавить provenance: commit/tree, dirty flag и воспроизводимый source
   identity; release delivery блокируется на dirty state.
6. Исправить project-local launcher precedence и stale override diagnostics.
7. Развести инструкции installation и onboarded self-project:
   - sibling/absolute workplace/project roots;
   - не направлять agent workflow в неполную distribution `.pf`;
   - добавить profile в `first-run` либо явно вести production setup через
     двухшаговый flow.
8. Обновить version/changelog/update metadata только после определения целевой
   версии.

### Tests

- intentional schema/checksum failure под `--only public-gate`;
- intentional resource parity failure;
- tampered README и binary entry при неизменном manifest;
- missing/extra/duplicate/casefold ZIP entry;
- clean и dirty provenance;
- distribution relocation через override/workplace/env;
- clean extraction с sibling paths, spaces и кириллицей;
- documented commands copy/paste test.

### Exit gate

Каждый intentional release defect даёт nonzero exit; чистый consumer может
проверить ZIP без source checkout.

## 10. Фаза 7 — dogfooding, независимый review и release candidate

### Findings

PF-AUD-026—PF-AUD-028 и полный regression shield.

### Последовательность

1. Исправить stale dogfooding path ожидание
   `processes/<id>.yaml` -> authoritative layout.
2. Исправить capability resolution в full resource-authoring chain.
3. Выполнить targeted negative regressions по всем PF-AUD.
4. Выполнить штатные source gates последовательно:

```text
python tools/validate-process-forge-schemas.py
python tools/validate-public-cleanliness.py
python tools/validate-process-forge-checksums.py --check
python bin/pf.py release-test --root . --public
git diff --check
```

5. Выполнить project-local dogfooding:
   - resource authoring;
   - resource management;
   - process authoring;
   - official pack activation/run;
   - launcher relocation.
6. Зафиксировать clean commit state.
7. Пересобрать только:
   - `dist/processforge.zip`;
   - `dist/processforge.manifest.json`.
8. Выполнить full extracted `release-archive-test`.
9. Независимый assurance reviewer сверяет finding disposition matrix и
   артефакты тестов.

### Exit gate

Review result `pass` либо `pass_with_conditions` без Critical/High waiver.
Публикация и push выполняются только после отдельного подтверждения.

## 11. Зависимости и допустимый параллелизм

```text
Фаза 0 Contract ADR
  ├─> Фаза 1 Security boundaries
  └─> Фаза 2 Schema/doctor alignment
         └─> Фаза 3 Transactional authoring
                ├─> Фаза 4 Lifecycle/context
                └─> Фаза 5 Providers/runtime surfaces
                       └─> Фаза 6 Release integrity/launcher/docs
                              └─> Фаза 7 Full assurance/release candidate
```

Фазы 1 и 2 могут частично идти параллельно только при непересекающихся файлах.
Поскольку большая часть реализации находится в `tools/processforge.py`, merge
в него выполняет один writer. Reviewer и test engineer начинают работу после
freeze соответствующего implementation slice.

## 12. Finding disposition matrix

| Findings | Фаза | Обязательность |
|---|---:|---|
| PF-AUD-001—002 | 1 | release blocker |
| PF-AUD-003—004 | 6 | release blocker |
| PF-AUD-005—006 | 2 | release blocker |
| PF-AUD-007—009, 017 | 4 | release blocker |
| PF-AUD-010—011 | 3 | release blocker |
| PF-AUD-012—013 | 1 и 5 | release blocker |
| PF-AUD-014—016, 018 | 6 | release blocker |
| PF-AUD-019—020 | 3 и 4 | fix or reviewed waiver |
| PF-AUD-021—022 | 5 | fix or reviewed waiver |
| PF-AUD-023—025 | 6 | fix before public release |
| PF-AUD-026—028 | 7 | fix or explicit time-bounded waiver |

## 13. Отчётность

В ходе выполнения поддерживать:

- `.pf/logs/pre-release-remediation-20260730.md`;
- отдельные subagent reports в
  `.pf/artifacts/pre-release-remediation-agents/`;
- ADR schema authority;
- итоговую matrix `finding -> files -> tests -> result -> residual risk`;
- `.pf/artifacts/pre-release-remediation-report-20260730.md`;
- `.pf/reviews/pre-release-remediation-review-20260730.md`;
- `.pf/handoffs/pre-release-remediation-release-handoff-20260730.md`.

Каждый substantive action логируется с временем, ролью, scope, файлами,
результатом, pending checks и residual risks.
