# Аудит: automatic projectors, стадии и технические obligation

Дата: 2026-08-14

## Итог

Первый полезный slice — **`required-output-readiness` для стадии `collect`
процесса `process-supervisor`**, а не `changed-files`.

Это техническая, детерминированная проекция: она отвечает, какие обязательные
outputs текущего PF worker task существуют, отсутствуют или больше не
соответствуют входному состоянию. Она не создаёт вторую модель задач и не
перезаписывает semantic artifacts.

`changed-files` остаётся кандидатом следующего этапа. Текущий Codex adapter
намеренно не кладёт `tool_input.command` и список файлов в durable event
payload, а снимок `git diff` нельзя задним числом честно восстановить из Event
Journal после restart. Делать из такого снимка первый authoritative projector
было бы недетерминированно.

## Текущее состояние

| Область | Подтверждённое состояние | Вывод |
| --- | --- | --- |
| Стадии | `processes/core/process-supervisor.yaml` описывает `prepare`, `start`, `collect`, их artifacts и gates. | Декларации уже достаточны для первой привязки. |
| Lifecycle | `worker-run` создаёт `status.json`, `command.json`, heartbeat, exit и collection report; Inspector остаётся владельцем этих фактов. | Projector должен читать, а не вычислять progress по heartbeat. |
| Required outputs | `required_output_checks()` и `task-doctor` проверяют пути из assignment. | Есть authoritative inputs, но пока нет durable projection/freshness view. |
| Event Journal | `worker.run.*`, `task.*`, `assignment.*`, `supervisor.tick.completed` и agent events пишутся в project journal. | Событие служит сигналом rebuild; оно не заменяет источник worker facts. |
| Projector | `tools/pf_runtime/host.py:rebuild_projection()` создаёт только `.pf/artifacts/projections/command-history.md` из `agent.*`. | Это automatic artifact, но не stage-aware и без doctor state. |
| Work state / MCP | `work_state_payload()` возвращает supervisor state, presence и event count; MCP читает тот же Ledger-bound payload. | Нужно добавить generic projection summary, не отдельный MCP state. |
| Runtime | Runtime после ingress rebuilds command history; scheduler отмечает projection `not_due`. | Нельзя переносить stage rules в Runtime; Runtime должен вызывать общий Core/Host projector. |

## Классификация артефактов

- **Automatic:** command history, agent-run records, supervisor state, required
  output file presence, projection readiness snapshot.
- **Semantic:** audit/report/rationale/handoff bodies, созданные человеком или
  моделью.
- **Hybrid:** assignment/run metadata — цель и scope semantic, но status и
  result facts могут обновляться PF CLI.

Проектор получает ownership только над отдельным техническим projection file.
Он не редактирует output/report/handoff и не добавляет managed section в
semantic document на первом slice.

## Выбранная привязка

Для `process-supervisor:collect` будет явно объявлена automatic obligation
`required-output-readiness`:

- входы: assignment `required_outputs`/`expected_report`, текущий agent-run
  status и фактическое существование разрешённых output files;
- activation: task с process `process-supervisor`, для которого worker дошёл до
  terminal state либо collection is pending;
- выход: отдельный JSON technical artifact под `.pf/artifacts/projections/`;
- состояния freshness: `current`, `stale`, `missing`, `invalid`;
- exit gate: существующий `required-outputs-present` получает machine-readable
  evidence от этой проекции, но semantic completion не переписывается.

Active stage выводится из фактов Inspector: нет agent-run — `prepare`; run
running — `start`; terminal run при task не collected — `collect`; collected
task — завершён. Это правило будет generic для declaration-driven stage
obligations, а не hardcode в Runtime.

## Требуемые минимальные изменения

1. Добавить явный declaration для automatic technical obligation в process
   definition и при необходимости узкий schema contract.
2. Реализовать generic projector registry/rebuild в Core/Runtime Host, который
   читает stage declaration, источники и пишет atomic projection artifact.
3. Добавить projection-aware doctor/gate: missing/stale/invalid должны быть
   различимы от успешной readiness.
4. Добавить projection summary в существующий `pf.work_state`; MCP остаётся
   read-only и следует уже проверенной Ledger session isolation.
5. Оставить `command-history` отдельной existing projection и поддержать
   rebuild обеих проекций без Runtime.

## Проверки следующего slice

- rebuild после удаления derived projection и после Runtime restart;
- missing/invalid/stale/current; два worker sessions одного project;
- изоляция двух projects и broken Project B без влияния на A;
- CLI без Runtime; cross-project MCP denial;
- semantic output не меняется projector'ом;
- живая Codex session: hook events, file edit, command/test, automatic
  projection/work-state/doctor без ручного служебного редактирования;
- независимый PF shell-worker review и повтор после remediation.

## Вне scope

Не меняются platform-resolution/classification, daemon lifecycle, Agent
Director decisions, write-MCP, новая БД, Server/Web sync и универсальный
workflow engine.
