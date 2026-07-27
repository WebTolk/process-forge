# Режимы Координации Проекта

ProcessForge разделяет capability уровня workplace и режим координации
конкретного проекта.

Workplace может поддерживать Director infrastructure, но это не делает все
проекты организованными. Каждый проект вычисляет свой effective mode:

- `simple`: по умолчанию работает одна primary agent session.
- `organized`: проект может использовать workplace Director Office, inbox,
  cases, leases, handoffs и связанную координацию.
- `inherit`: проект наследует `workplace.coordination.default_project_mode`.

## Capability Workplace

`workplace.yaml` хранит machine-level capability:

```yaml
coordination:
  director_enabled: true
  director_office_enabled: true
  default_project_mode: simple
```

`director_enabled: true` означает, что Director coordination доступна в
workplace. Это не означает, что каждый проект обязан работать через Director.

Director Office остаётся единым для workplace:

```text
<workplace>/.pf/director/
```

Он содержит inbox, outbox, cases, history, runs, artifacts, continuations и
runtime directories. ProcessForge не создаёт отдельный Director Office для
каждого проекта по умолчанию.

## Режим Проекта

Project manifest использует:

```yaml
coordination:
  mode: inherit
  director:
    use_workplace_director: true
    inbox_submit_required: false
```

Правила resolution:

- явный `simple` всегда остаётся simple, даже если Director есть в workplace.
- явный `organized` требует workplace Director capability и initialized
  Director Office.
- `inherit` следует workplace default.

Команды:

```bash
python bin/pf.py project-mode status --project-root <project> --workplace <workplace> --json
python bin/pf.py project-mode set --project-root <project> --mode simple
python bin/pf.py project-mode set --project-root <project> --mode organized --init-office
python bin/pf.py project-mode doctor --project-root <project>
```

## Director Inbox И Cases

`director-inbox-submit` принимает project-scoped worker reports для organized
projects. Simple project по умолчанию получает ясный отказ: Director может быть
доступен в workplace, но сам проект намеренно остаётся simple.

`director-case-refresh` читает project context snapshots, а не весь source tree.
Он создаёт cases для organized projects и проектов с открытыми Director inbox
items. Simple projects игнорируются, если не указан `--include-simple`.

## Осведомлённость Worker

`project-context-refresh` записывает `workplace_coordination` в snapshots.

Для simple projects:

```yaml
workplace_coordination:
  effective_mode: simple
  director_available_at_workplace: true
  director_required: false
```

Для organized projects snapshots и capsules содержат Director inbox metadata,
когда это нужно. Simple capsules не требуют Director inbox submission или
worker reports to Director.

## Error Workflow

Error handling учитывает effective project mode:

- `director_inbox` требует organized mode.
- simple projects могут fallback к `needs_operator`.
- `route_to_process` работает в simple mode, если есть process route.
- `needs_operator` и `none` допустимы во всех режимах.
