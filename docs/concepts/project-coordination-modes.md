# Project Coordination Modes

ProcessForge separates workplace capability from project coordination mode.

A workplace can support Director infrastructure without forcing every project
to use it. Each project resolves its own effective mode:

- `simple`: one primary agent session works the project by default.
- `organized`: the project can use the workplace Director Office, inbox, cases,
  leases, handoffs, and related coordination.
- `inherit`: the project follows `workplace.coordination.default_project_mode`.

## Workplace Capability

`workplace.yaml` owns machine-level capability:

```yaml
coordination:
  director_enabled: true
  director_office_enabled: true
  default_project_mode: simple
```

`director_enabled: true` means Director coordination is available in the
workplace. It does not mean all projects are organized.

The Director Office is workplace-level:

```text
<workplace>/.pf/director/
```

It contains inbox, outbox, cases, history, runs, artifacts, continuations, and
runtime directories. ProcessForge does not create a separate Director Office
per project by default.

## Project Mode

Project manifests use:

```yaml
coordination:
  mode: inherit
  director:
    use_workplace_director: true
    inbox_submit_required: false
```

Effective mode resolution:

- explicit `simple` always stays simple, even when workplace Director exists.
- explicit `organized` requires workplace Director capability and an initialized
  Director Office.
- `inherit` follows the workplace default.

Use:

```bash
python bin/pf.py project-mode status --project-root <project> --workplace <workplace> --json
python bin/pf.py project-mode set --project-root <project> --mode simple
python bin/pf.py project-mode set --project-root <project> --mode organized --init-office
python bin/pf.py project-mode doctor --project-root <project>
```

## Director Inbox And Cases

`director-inbox-submit` allows project-scoped worker reports for organized
projects. Simple projects fail clearly by default because the workplace Director
may exist while the project is intentionally simple.

`director-case-refresh` reads project context snapshots, not full source trees.
It creates cases for organized projects and projects with open Director inbox
items. Simple projects are ignored unless `--include-simple` is explicit.

## Worker Awareness

`project-context-refresh` writes `workplace_coordination` into snapshots.

For simple projects:

```yaml
workplace_coordination:
  effective_mode: simple
  director_available_at_workplace: true
  director_required: false
```

For organized projects, snapshots and capsules include Director inbox metadata
when relevant. Simple capsules do not require Director inbox submission or
worker reports to Director.

## Error Workflow

Process error handling respects effective project mode:

- `director_inbox` requires organized mode.
- simple projects can fall back to `needs_operator`.
- `route_to_process` works in simple mode when a process route exists.
- `needs_operator` and `none` are valid in all modes.

Use:

```bash
python bin/pf.py error-route --project-root <project> --mode director_inbox --fallback-if-no-director needs_operator
```
