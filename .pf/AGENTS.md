<!-- PF:ENTRY:BEGIN contract=1.1.1 -->
## ProcessForge startup contract

This project is governed by ProcessForge (PF). This section is the startup
contract; `.pf/` holds state and further instructions. It grants no file,
tool, resource, process or infrastructure permissions by itself.

1. Locate this project's `.pf/process-forge.yaml` and read it. Call `pf.context`
   for this project root. If MCP is unavailable, use the existing project PF
   CLI and current `.pf/contexts/project-context.snapshot.yaml`; check freshness
   with `project-context-check`. Do not install or start tools to obtain context.
2. Before substantive work, require a valid, current context with no blocking
   readiness or policy result. Missing, stale, broken, conflicting or ambiguous
   context means stop the dependent work and report the exact blocker and
   required operator action. Historical reports do not override current state.
3. For continuation, discover candidates through `pf.continuation.status` or
   read the named continuation. Select exact run/assignment/context ids, create
   a continuation with explicit apply if needed, then `pf.continuation.resume`.
   Missing or ambiguous selection must not create Work. Without a bound session,
   pass returned selectors to every Work call. Use `pf.work.start` for new work.
   Follow PF's returned identity; never choose the first or newest assignment.
   If `process_choice_required`, select only an offered process and call again
   with `process_id`; do not infer a choice from a default among alternatives.
   If the objective cannot disambiguate the choice, ask the user.
4. Read `pf.work.state`, its selected assignment and immutable context capsule.
   Verify matching project/run/assignment/context identity, validity, current
   stage, allowed actions, read/write scope and obligations before acting.
   Empty grants grant nothing. A denied action or required unavailable resource
   blocks dependent work; do not broaden scope or rebuild the capsule yourself.
5. Use `pf.search`/`pf.resolve` for authorized project navigation. For Work
   resources use `pf.work.search`/`pf.work.resolve` with the exact returned run,
   assignment and context ids. Resolve before opening PF-managed resource roots;
   load only the authorized instructions, knowledge and templates needed now.
6. Satisfy the current stage, record artifacts/evidence and call
   `pf.work.transition` with outcome and evidence. The pinned process selects
   stages: never supply `next_stage` or edit lifecycle state manually. Repeat
   state/work/transition until PF returns `action: run_completed`. Use equivalent
   existing CLI operations when MCP is unavailable; do not invent commands.
7. Respect one writer per scope. Keep approved artifacts, process versions and
   capsules immutable. Use a governed handoff for scope/context changes. Keep
   arbitrary agent scratch only under this project's `.pf/tmp/`; remove it unless
   retained as evidence. Durable artifacts keep their established locations;
   atomic replacement staging stays beside its destination. Age alone never
   authorizes deletion.
   Never put private paths, credentials or machine details in public outputs.
8. Ordinary work must not install, start, restart or repair PF Runtime, MCP,
   host hooks or Agent Ledger. Report infrastructure blockers to the operator.
   File-only work does not require these services. Completion handoffs are
   advisory and do not authorize infrastructure or external-session actions.

Specialized work begins only after PF resolves its valid context and obligations.
This text defines conduct; technical access enforcement belongs to the host/PF.
<!-- PF:ENTRY:END -->

## Текущий dev-этап

- Выполняйте только рефакторинг существующего функционала PF. Сохраняйте внешний
  контракт публичного релиза: CLI/MCP, параметры, payloads, ошибки и форматы.
- Новые функции и расширения фиксируйте как будущие задачи; не реализуйте их
  в текущем рефакторинге. Не добавляйте внутреннюю обратную совместимость и
  дополнительные тесты только ради переноса; используйте необходимые имеющиеся
  точечные проверки.
- Сверяйтесь с базовыми архитектурными документами в `.pf` и используйте локальные
  знания Python, выбранные и разрешённые ProcessForge для текущей Work.

## Режим команды 1-1-4

- Если пользователь задаёт режим `1-1-4`, основной агент совмещает оркестрацию и
  исполнение; один независимый ревьювер проверяет результат основного агента и
  всех воркеров; четыре воркера получают отдельные ограниченные задачи.
- Количество воркеров можно увеличить по необходимости. Число обозначает состав
  команды, а не требование одновременно запускать всех участников.
- Используйте нативных shell-воркеров PF с отдельными Work, точными selectors,
  неизменяемыми capsules и регистрацией в Agent Ledger. Координацию, поручения,
  подтверждения чтения и передачу результатов ведите через сообщения PF.
- До запуска закрепляйте владельцев непересекающихся областей записи и ожидаемые
  отчёты. Основной агент отвечает за интеграцию и итоговую доставку. Ревьювер
  начинает проверку после завершения реализации и не проверяет собственный код.
- Для Python используйте знания, выбранные и разрешённые PF для соответствующей
  Work. Не подменяйте их устаревшими заметками или глобальным legacy workflow.

## Коммиты и доставка

- Каждую завершённую задачу фиксируйте отдельным локальным коммитом. По умолчанию
  после задачи остановитесь; явно порученный пользователем блок или цикл доведите
  только до согласованной границы и затем остановитесь с отчётом.
- Один и тот же коммит отправляйте параллельными push в оба remote:
  `origin` (GitHub) и `gitverse` (GitVerse). Правило действует для обоих агентов.
- Для текущей dev-работы после push прочитайте обе удалённые ветки `dev` и
  подтвердите одинаковый полный SHA коммита. Успех только одного push оставляет
  доставку незавершённой; повторяйте недостающую публикацию без нового коммита.
- Включайте в коммит только собственные изменения текущей задачи, сохраняя чужое
  dirty/staged состояние. Не записывайте секреты в URL, аргументы и артефакты.


## Standard Statuses

Artifact statuses:

```text
missing
draft
ready_for_review
approved
rejected
stale
superseded
archived
```

Review result statuses:

```text
pass
pass_with_conditions
warn
fail
skipped
```

Upgrade assessment results:

```text
safe
requires_approval
requires_migration
blocked
```

## Logging Format

Use append-only log entries:

```markdown
## YYYY-MM-DD HH:MM - <role>

Task:
Files changed:
Artifacts changed:
Templates used:
Tools used:
Decisions:
Risks:
Next steps:
Handoff:
```

## Handoff Format

```markdown
# Handoff: <from> -> <to>

Objective:
Current status:
Input artifacts:
Files changed:
Files not to touch:
Known issues:
Required checks:
Next recommended action:
```
