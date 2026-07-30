# Отчёт transaction reviewer

- Assignment: `remediation-transaction-review-20260730`
- Run: `pre-release-remediation-20260730`
- Agent: `codex-remediation-transaction-reviewer`
- Session: `pre-release-remediation-20260730-transaction-review`
- Lease: `lease-remediation-transaction-review-20260730`
- Результат: **FAIL**
- Product writes: отсутствуют

## Краткий вывод

Обычные in-process rollback сценарии заметно улучшены:

- все шесть команд требуют ровно один explicit mode;
- knowledge manifest/index и private registry откатываются вместе;
- platform install использует canonical layout;
- legacy platform state отвергается;
- process-create не пишет в uninitialized root;
- process dry-run показывает 16 entity files, 6 событий и 12 условных hook
  destinations.

Однако frozen slice имеет три подтверждённых release blocker:

1. platform authoring не запускает staged/public doctor checks, но публикует
   `available`, `doctor.passed` и `completed`;
2. crash recovery не проверяет pre-image hash и не удаляет созданные каталоги,
   однако ставит `rolled_back`;
3. post-commit replay повторяет уже завершённые эффекты, не имеет recovery CLI
   и не достигает terminal audit-complete state.

Дополнительно сохранены запрещённые strict policy deprecated aliases, а dry-run
не вызывает общий pure preflight.

## Подтверждённые результаты

### PASS

```text
all six XOR modes: nonzero + no writes
legacy layout and dual layout: rejected + no writes
platform-contract-migrate parser command: absent
knowledge after entity 1: exact rollback
knowledge after entity 2: exact rollback
knowledge after private registry 1: exact rollback
process uninitialized: no .pf/session/events
process dry-run: 16 entity + 6 audit + 12 conditional hook rows
three dedicated smokes: PASS
seven related process/platform regressions: PASS
schema validator: PASS
```

### FAIL

Platform semantic failure:

```text
create_rc=0
registry_status=available
doctor_rc=1
doctor_passed_event=True
completed_event=True
```

Crash recovery:

```text
incomplete journal blocked mutation=True
recovery_state=rolled_back
created authoritative directories left behind=True
corrupted backup accepted=True
restored SHA equals pre_sha256=False
```

Post-commit retry:

```text
first state=committed_audit_pending
first completed=[one]
effect one executions after retry=2
state after all effects=committed_audit_pending
public replay command=absent
```

Dry-run/apply feasibility:

```text
regular-file index parent:
dry-run rc=0
apply rc=1
both write-free=True
```

Strict parser:

```text
platform-create --package ... --dry-run rc=0
deprecated platform aliases remain advertised
process-authoring-apply --id remains advertised as Compatibility alias
```

## Source defects

- `build_platform_authoring_plan`: `validation_callbacks=[]`;
- platform post-commit callback emits doctor PASS/completed literally;
- `rollback_authoring_plan`: no restored hash verification;
- `recover_authoring_transaction`: no hash verification or created-directory
  cleanup;
- `run_post_commit_effects`: ignores prior successes and does not close pending
  audit state;
- `incomplete_authoring_journals`: treats audit pending as terminal;
- no command rehydrates/replays journal effects;
- dry-run handlers render without `preflight_authoring_plan`;
- parser still accepts deprecated aliases.

## Минимальное исправление

1. Общий pure platform checker должен работать и на staged virtual view, и в
   public doctor; registry `available` публикуется только после него.
2. Recovery удаляет created dirs, проверяет каждый `pre_sha256`/absence и
   оставляет `recovery_required` при любой недоказанной операции.
3. Journal хранит versioned rehydratable effects со stable `effect_id`,
   payload/idempotency key и per-effect state. Replay пропускает succeeded,
   продолжает pending/failed, а sinks дедуплицируют stable effect id.
4. Добавляется public/automatic `authoring-transaction-recover`.
5. Только `rolled_back` и `committed_audit_complete` считаются terminal;
   `committed_audit_pending` требует replay и проваливает health/release gate.
6. Dry-run вызывает pure common preflight; deprecated aliases удаляются.

Полная evidence matrix, строки символов, тесты и required disposition находятся
в:

`.pf/reviews/pre-release-remediation-transaction-review-20260730.md`.
