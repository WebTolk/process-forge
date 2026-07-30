# Минимальный patch scope: transaction blockers

- Date: 2026-07-30
- Basis:
  `.pf/reviews/pre-release-remediation-transaction-review-20260730.md`
- Mode: report-only
- Product files changed: none

## Итог

Три подтверждённых блокера закрываются локальным изменением существующей
transaction layer и трёх planners. Переписывать authoring masters или вводить
отдельный transaction package не требуется.

Минимальный обязательный product scope:

```text
tools/processforge.py
tools/smoke_remediation_transactional_authoring.py
tools/smoke_remediation_process_create_transaction.py
tools/smoke_remediation_transaction_recovery.py   # новый узкий smoke
```

`build_parser` всё равно потребуется для recovery command, поэтому удаление
расположенных рядом strict aliases допустимо в том же slice. Другие
compatibility поверхности в эту задачу не включать.

## 1. Staged platform semantic validation

### Изменяемые функции

- `resolve_platform_contracts` — примерно `3765-3911`;
- `command_platform_contract_doctor` — примерно `21090-21251`;
- `build_platform_authoring_plan` — примерно `22255-22444`;
- неизменяемые handlers:
  `command_platform_create` (`22447+`) и
  `command_platform_contract_install` (`22503+`) уже вызывают общий executor.

### Минимальная реализация

1. Добавить к `resolve_platform_contracts` optional
   `contract_overrides: dict[str, dict[str, Any]] | None`.
   Внутренний `resolve_one` сначала берёт staged contract из override, иначе
   вызывает текущий `load_platform_contract`. Этого достаточно для проверки
   нового контракта вместе с live parent contracts без публикации registry.
2. Вынести только blocking semantic часть public doctor в один helper, например:

   ```text
   platform_contract_semantic_checks(
       workplace_root,
       contract_data,
       platform_resolution,
   ) -> list[Check]
   ```

   Он покрывает invalid/optional parent refs, weakening parent requirement,
   missing required platforms, cycles, required resources и invalid resolved
   stack. Public doctor расширяет результат этим helper.
3. В `build_platform_authoring_plan` добавить
   `validate_platform_plan(plan, staged)`:
   - прочитать staged `platform-contract.yaml`;
   - повторно проверить JSON Schema;
   - вызвать `resolve_platform_contracts(..., contract_overrides={contract_id:
     candidate})`;
   - вызвать общий semantic helper;
   - при любом `FAIL` остановить transaction до entity/registry publication.
4. Передать callback как:

   ```text
   validation_callbacks=[validate_platform_plan]
   ```

5. Существующий post-commit effect может публиковать
   `platform.contract.doctor.passed` и `platform.authoring.completed` только
   после успешного callback. Не добавлять второй post-commit doctor.

Не нужен temporary live registry, публикация entity до doctor или отдельная
platform transaction implementation.

### Smoke

Расширить `tools/smoke_remediation_transactional_authoring.py` одним тестом:
schema-valid staged contract с `requires.platforms =
platform.missing-parent`. Проверить nonzero и exact fingerprint:

```text
contract absent
platform registry byte-identical/no available
events byte-identical/no doctor.passed/no completed
```

## 2. Verified rollback and recovery

### Изменяемые функции

- `rollback_authoring_plan` — примерно `649-684`;
- `recover_authoring_transaction` — примерно `755-778`;
- `incomplete_authoring_journals` — примерно `480-490`;
- локально можно добавить два небольших helper рядом:

  ```text
  restore_authoring_record(record, transaction_id)
  verify_authoring_rollback(journal) -> list[str]
  ```

### Минимальная реализация

Оба rollback пути используют один restore/verify contract:

1. Для `pre_exists: true` перед восстановлением доказать, что backup существует
   и его SHA-256 равен `pre_sha256`. Corrupt backup не копировать поверх
   destination.
2. Восстановить backup через temporary + `os.replace`, сохраняя backup до конца
   полной проверки.
3. Для `pre_exists: false` удалить опубликованный destination.
4. В reverse order удалить каждый путь из `created_directories`, только если он
   пуст.
5. После всех операций проверить:
   - каждый pre-existing destination является file с точным `pre_sha256`;
   - каждый pre-missing destination отсутствует;
   - созданные transaction каталоги вне journal/staging отсутствуют.
6. Только при пустом списке ошибок установить `rolled_back` и
   `rollback_verified: true`. Иначе:

   ```text
   state: recovery_required
   rollback_verified: false
   recovery_errors: [...]
   ```

   и оставить последующие mutations заблокированными.

`recover_authoring_transaction` до filesystem operations должен проверить
journal object, transaction id, writes list, absolute destination/backup paths
и containment backup внутри transaction root. Широкая JSON Schema migration
для этого patch не требуется; достаточно закрытой internal validation function.

### Smoke

Новый `tools/smoke_remediation_transaction_recovery.py` содержит ровно два
subprocess-crash сценария:

1. `os._exit` после публикации нового nested file: recovery удаляет file и все
   созданные authoritative parent dirs, затем unblocks.
2. `os._exit` после replace existing file, затем corrupt backup:
   recovery возвращает/ставит `recovery_required`, destination не признаётся
   восстановленным, следующая mutation остаётся blocked.

Проверять файлы, каталоги и SHA-256, не только journal state.

## 3. Idempotent durable post-commit replay

### Изменяемые структуры и функции

- `AuthoringEffect`/`AuthoringPlan` — примерно `412-430`;
- `stage_authoring_plan` — примерно `552-592`;
- `run_post_commit_effects` — примерно `725-738`;
- `execute_authoring_plan` — примерно `741-752`;
- `incomplete_authoring_journals` — примерно `480-490`;
- `process_authoring_event_effect` — примерно `12563-12586`;
- `build_process_create_plan` effects — примерно `12703-12753`;
- knowledge effects in `build_knowledge_resource_add_plan` —
  примерно `20742-20806`;
- platform effects in `build_platform_authoring_plan` —
  примерно `22402-22442`;
- `build_parser` — примерно `22519+`;
- новый handler рядом с transaction helpers:
  `command_authoring_transaction_recover`.

### Минимальный durable contract

Нельзя сериализовать closures. Необходимо заменить только пять текущих
`AuthoringEffect(...)` call sites на serializable effect descriptors.

Добавить в `AuthoringEffect`:

```text
effect_id
kind
payload
executable: bool
```

`stage_authoring_plan` сохраняет в journal ordered
`post_commit_effects` с:

```text
effect_id
kind
payload
state: pending
attempts: 0
last_error: null
```

`effect_id` детерминирован:
`<transaction-id>:<ordinal>:<kind>`. Conditional hook rows, существующие только
для dry-run visualization, получают `executable: false` и не считаются
выполненными audit effects.

Добавить один dispatcher:

```text
execute_authoring_effect(effect_record)
```

с тремя поддерживаемыми kinds:

- `process_event`;
- `knowledge_audit`;
- `platform_audit`.

Payload содержит уже вычисленные transaction id, roots, subject ids,
proposal/report/event data. Не хранить callbacks.

Перед side effect записать `state: running`, увеличить attempts; после успеха
записать `succeeded`. Replay пропускает `succeeded` и выполняет только
`pending|running|failed`. Для crash между sink write и journal success sink
должен получать stable `effect_id` как event/proposal/hook idempotency key.
`process_authoring_event_effect` больше не генерирует новый event identity при
каждом вызове.

После всех executable effects:

```text
state: committed_audit_complete
```

При ошибке:

```text
state: committed_audit_pending
effect.state: failed
effect.last_error: ...
```

Terminal для mutation/recovery health:

```text
rolled_back
committed_audit_complete
```

`committed`, `committed_audit_pending` и `recovery_required` нельзя считать
полностью завершёнными. Pending audit не откатывает authoritative state, но
обязан быть видим recovery/doctor path.

### Recovery command

В `build_parser` добавить один explicit-mode command:

```text
authoring-transaction-recover
  --runtime-root <path>
  --transaction <id>
  (--dry-run | --apply)
```

- pre-commit state: показать/выполнить verified rollback;
- committed/audit-pending: показать/выполнить оставшиеся effects;
- recovery-required: повторить verified recovery;
- terminal state: no-op PASS с текущим state.

Это единственный новый public command; отдельные platform/knowledge/process
replay commands не нужны.

### Smoke

В `tools/smoke_remediation_transaction_recovery.py` добавить один effect test:

1. effect A succeeds;
2. effect B fails;
3. journal содержит A succeeded/B failed;
4. recovery command executes B only;
5. A sink count остаётся `1`, B становится `1`;
6. journal становится `committed_audit_complete`;
7. повтор recovery — no-op без duplicate.

В `tools/smoke_remediation_process_create_transaction.py` добавить проверку,
что replay одного process event с тем же `effect_id` не создаёт второй event/
hook delivery.

## Adjacent strict aliases

`build_parser` уже изменяется для recovery command, поэтому в том же patch
удалить:

- `platform-create --package`, `--knowledge-package`, `--template`, `--tool`,
  `--mcp` — примерно `22994-22998`;
- `process-authoring-apply --id` — примерно `23212`;
- соответствующее чтение deprecated platform args в
  `platform_authoring_values` — примерно `22020-22045`;
- fallback `args.process or args.id` в `command_process_authoring_apply` —
  примерно `12767`.

Не расширять этот patch на aliases других, не затронутых transaction commands.

## Порядок одного writer

1. verified rollback/recovery helpers;
2. durable effect journal + recovery command;
3. перевод трёх planners на serializable effects;
4. staged platform semantic callback;
5. adjacent parser cleanup;
6. три targeted smoke files;
7. связанные regressions и schema/public gates.

Один writer должен владеть `tools/processforge.py` на всём протяжении patch.
`dist/**`, checksums, docs, release metadata и другие lifecycle masters не
входят в scope.
