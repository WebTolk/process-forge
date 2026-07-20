# Workplace Init

Workplace Init creates the machine-local ProcessForge layer.

It answers:

```text
What is available on this machine and where is it?
```

The workplace layer is not a project. It records local capabilities, roots,
registries, cache, runtime state, logs, and policies that a project may use
through explicit resolution.

## Command Model

```bash
python bin/pf.py workplace-init --workplace <workplace-root> --dry-run
python bin/pf.py workplace-init --workplace <workplace-root> --apply
python bin/pf.py doctor-workplace --root <workplace-root>
```

`init-workplace --root <workplace-root>` is the lower-level command name.
`workplace-init --workplace <workplace-root>` is the first-run alias used in
public docs. `--dry-run` shows planned files. `--apply` writes files and runs
`doctor-workplace`.

## Created Files

`build_workplace_files()` currently writes:

```text
AGENTS.md
workplace.yaml
terms.yaml
registries/distributions.yaml
registries/platforms.yaml
registries/knowledge-roots.yaml
registries/package-roots.yaml
registries/templates.yaml
registries/tools.yaml
registries/mcp.yaml
logs/workplace-init-report.md
artifacts/workplace-bootstrap-report.md
reviews/workplace-bootstrap-review.md
handoffs/workplace-ready-handoff.md
```

The command also creates workplace directories needed by the manifest and
runtime flow, including `registries/`, `cache/`, `runtime/`, `logs/`,
`artifacts/`, `reviews/`, and `handoffs/`. Runtime events are written under
`runtime/events/events.ndjson`.

## Safety

- Do not store credentials or secret values.
- Use `auth_ref`, `credential_ref`, or `secret_ref` when a provider needs
  authentication.
- Keep workplace-local absolute paths in the workplace layer only.
- Project public files must refer to local config by relative file name, not by
  absolute path.

## Outputs

Workplace Init creates a human-readable `AGENTS.md`, a machine-readable
`workplace.yaml`, registry files, terms aliases, bootstrap artifacts, and a
workplace init report under `logs/`.
