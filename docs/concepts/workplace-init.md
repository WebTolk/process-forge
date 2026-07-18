# Workplace Init

Workplace Init creates the machine-local ProcessForge layer.

It answers:

```text
What is available on this machine and where is it?
```

The workplace layer is not a project. It records local capabilities, roots, registries, cache, runtime state, and policies that a project may use through explicit resolution.

## Command Model

Future CLI:

```bash
processforge init workplace
processforge doctor workplace
```

MVP script equivalent:

```bash
python bin/pf.py workplace-init --workplace <workplace-root> --dry-run
python bin/pf.py workplace-init --workplace <workplace-root> --apply
python bin/pf.py doctor-workplace --root <workplace-root>
```

`--dry-run` is proposal-first and does not write files. `--apply` writes the files.

## Created Files

```text
AGENTS.md
workplace.yaml
terms.yaml
registries/platforms.yaml
registries/knowledge-roots.yaml
registries/package-roots.yaml
registries/templates.yaml
registries/tools.yaml
registries/mcp.yaml
cache/
runtime/
logs/
```

## Safety

- Do not store credentials or secret values.
- Use `auth_ref`, `credential_ref`, or `secret_ref` when a provider needs authentication.
- Keep workplace-local absolute paths in the workplace layer only.
- Project public files must refer to local config by relative file name, not by absolute path.

## Outputs

Workplace Init creates a human-readable `AGENTS.md`, a machine-readable `workplace.yaml`, registry files, terms aliases, and a workplace init report under `logs/`.
