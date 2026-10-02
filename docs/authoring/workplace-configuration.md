# Workplace configuration

`configuration.yaml` in the workplace directory stores operational settings.
It is separate from the identity, resource and policy manifest `workplace.yaml`.
Changing the statistics interval does not invalidate project context snapshots.
Project-context freshness still belongs to a particular project; the monitor
reports the age of the workplace activity sample, not aggregate context freshness.

```yaml
schema_version: 1
runtime:
  metrics:
    interval_seconds: 10
```

The interval accepts finite numbers from 1 to 60 seconds. Use 1–2 for small
workplaces and 10 for busier ones. New workplaces receive this file. Existing
workplaces without it use defaults without creating a file on read. An empty
mapping `{}` also uses defaults; an empty document, unknown keys, duplicate keys,
YAML aliases, incorrect types and unsupported schema versions are errors.
The file is limited to 64 KiB. The template is
[`templates/workplace-configuration.yaml`](../../templates/workplace-configuration.yaml).

## Core API

`PFConfig`, `RuntimeConfig` and `MetricsConfig` are immutable value classes.
`ConfigService` implements CRUD through an injected `ConfigStore` protocol.
Neither layer discovers directories, reads environment variables, imports CLI
code or depends on YAML. CLI, HTTP, MCP or another caller can share this API.
`YamlConfigStore` is a separate filesystem adapter taking an explicit absolute
file path. Applications select the workplace and compose the service themselves.

```python
from processforge_core.configuration import ConfigService, PFConfig
from processforge_core.configuration.yaml_store import YamlConfigStore

# The caller supplies workplace_root as an absolute pathlib.Path.
service = ConfigService(YamlConfigStore(workplace_root / "configuration.yaml"))
created = service.create(PFConfig())  # refuses to overwrite an existing file
current = service.read()            # config, revision, exists
updated = service.update(
    {"runtime.metrics.interval_seconds": 2},
    expected_revision=current.revision,
)
service.reset("runtime.metrics.interval_seconds", expected_revision=updated.revision)
service.delete()                    # removes the file; defaults apply afterwards
```

`update` and `reset` require an existing file. Updates accept dotted mutable
setting names; `schema_version` is not mutable through CRUD. `get` can read a
setting or section. `to_dict` returns a copy. Errors derive from
`ConfigurationError` and expose stable `code` values; conflicts derive from
`ConfigurationConflict`.

## CLI

From a source checkout, substitute `python -B tools/processforge.py` for `pf`.
The workplace directory must already exist; either its directory or its
`workplace.yaml` path is accepted.

```sh
pf config create --workplace <workplace-root>
pf config read --workplace <workplace-root> --json
pf config update --workplace <workplace-root> --key runtime.metrics.interval_seconds --value 2
pf config delete --workplace <workplace-root> --key runtime.metrics.interval_seconds
pf config delete --workplace <workplace-root>
```

`--value` uses JSON scalar syntax. `delete --key` resets that setting to its
default; `delete` without a key removes the configuration file. Mutation output
includes the resulting configuration and revision. Pass `--if-revision` to
`update` or `delete` to reject a revision changed since a client's earlier read.
Exit codes: 0 success, 1 invalid configuration/storage, 2 invalid command
arguments, 3 revision/missing-file/writer conflict. `--json` emits one JSON object
including on domain errors, without decoration or unrelated diagnostic files.

The YAML adapter checks the revision again under a nonblocking OS writer lock.
Writes use a flushed temporary file in the same directory and an atomic rename.
Existing Windows owner/group/DACL are restored and verified on the staged file
before rename; existing POSIX permission bits are preserved. New POSIX files
use mode 0600. Extended POSIX ACL preservation is not guaranteed. Linked and
nonregular targets are refused. A persistent `configuration.yaml.lock` remains
after mutations; do not remove it while writers may be running. These locks
coordinate cooperating local clients, not arbitrary editors or network storage.
CRUD rewrites canonical YAML and does not preserve comments or formatting.

## Runtime and monitor

Runtime validates configuration before creating its token. Its independent
statistics observer reloads the file at the beginning of each cycle. Changes
take effect on that next cycle, without a restart; invalid reloads keep the
last valid value and report `configuration_invalid`. Removing the file restores
the default. `doctor-workplace` validates the optional file too.

Collection is serial and separate from the project scheduler. A slow collection
skips missed periods instead of spawning another collection or catching up in
a burst. Filesystem delays and observation budgets can make samples late or
partial; a one-second period is not a one-second completion guarantee.

The monitor follows the applied Runtime interval unless `--interval` explicitly
overrides the viewer. Overriding the viewer does not change collection frequency.
Runtime works without a visible window, including servers accessed over SSH.
Launch `pf monitor` explicitly for the compact view, `--details` for diagnostics,
or `--json` for one undecorated observation. See
[Runtime monitor](../concepts/runtime-monitor.md).

## Workplace initialization and manifest

Use Workplace Init when setting up a machine or runner host. Start with
`templates/workplace-init.answers.yaml`: set workplace id, name, type, operating
system and root path; optionally supply knowledge, package, template, tools and
MCP roots.

```sh
python bin/pf.py workplace-init --workplace <workplace-root> --apply
python bin/pf.py doctor-workplace --root <workplace-root>
```

### Inherited project parameters

Workplace defaults for structured parameters can be declared directly in the
workplace answers/manifest or in `<workplace-root>/registries/parameters.yaml`.
Use these for machine-local defaults inherited by projects: local test stands,
publication channels, render presets, accounting profiles or another
domain-neutral parameter tree. ProcessForge stores and merges the structure;
it does not interpret the namespace.

Projects override these values through `.pf/process-forge.yaml`, private
`.pf/process-forge.local.yaml` `overrides.parameters`, `.pf/parameters.yaml`, or
`.pf/parameters.local.yaml`. The project context snapshot receives the computed
`resolved_parameters` tree and `parameter_resolution` provenance. Do not put
parameters in `AGENTS.md` expecting the resolver to parse Markdown instructions.

### Path constants

Define reusable path bases in `workplace.yaml`:

```yaml
path_constants:
  PF_WORKPLACE: "."
  PF_KNOWLEDGE: "knowledge"
  PF_TEMPLATES: "reusable-templates"
  PF_TOOLS: "tools"
```

Registry entries may use `${PF_KNOWLEDGE}/joomla/docs` or an explicit absolute
path. Absolute paths are allowed in workplace/private files, but never in
public project snapshots. Run
`python bin/pf.py path-resolve --workplace <workplace-root> --path '${PF_KNOWLEDGE}/joomla/docs'`
to inspect expansion.

### Package roots

Configure package roots in `registries/package-roots.yaml`:

```yaml
package_roots:
  - id: global
    path: ${PF_WORKPLACE}/packages
    status: available
    writable: true
    default: true
```

Package roots control where Resource Management reads and writes knowledge
packages. With multiple candidates for the same package id, write commands
require `--package-root <id>` to avoid updating the wrong copy.
`doctor-workplace` validates root ids, path constants, availability and writability.
