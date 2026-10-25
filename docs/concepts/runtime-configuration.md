# Hook collection and session lifecycle

Native CLI/MCP operations pin the full merged configuration for their selected
project/workplace. Nested calls that omit a device selector inherit that same
operation snapshot; they do not reopen the default device YAML. Context-local
storage routing supplies only matching authorized targets to legacy adapters.
Leaving an operation restores the previous selection, including on exceptions.

For project scratch and configurable old-file reminders, see
[temporary files](../temporary-files.md). These notifications do not delete files.

Automatic agent hooks use the project's effective coordination mode, including
workplace inheritance. Forge (`organized`) always admits the gatekeeper.
Garage (`simple`) ignores hooks by default; its operator can opt in through
PFConfig. Runtime availability does not select the project mode.

The workplace default is stored in `configuration.yaml`:

```yaml
schema_version: 1
runtime:
  garage_hooks: false
```

A project's `.pf/configuration.yaml` can override it:

```yaml
schema_version: 1
runtime:
  garage_hooks: true
```

An absent override or `garage_hooks: null` inherits the workplace value. Global
values must be booleans; project values are booleans or null. Existing live
configuration reload and last-valid error handling apply. This flag cannot
disable Forge; it only controls automatic hooks in Garage.

Use the existing typed configuration commands:

```bash
python bin/pf.py config update --workplace <workplace> --key runtime.garage_hooks --value true
python bin/pf.py config update --workplace <workplace> --project-root <project> --key runtime.garage_hooks --value false
python bin/pf.py config delete --workplace <workplace> --project-root <project> --key runtime.garage_hooks
python bin/pf.py config read --workplace <workplace> --project-root <project> --key runtime.garage_hooks --json
```

Deleting a project key restores inheritance. Existing `logging.raw_hooks` and
`logging.events` settings independently control optional records after hook
admission. Explicit Core/CLI operations, worker report collection and governed Work outputs remain
available when automatic Garage hooks are disabled.

The hook prefers authenticated app-server delivery and falls back to the same
Host/Core implementation through CLI. Disabled Garage hooks stop before raw
receipts, project events/chat, Ledger enrollment or deferred payload writes.
They return the existing neutral observer response: `{}` for Stop/SubagentStop
and empty output for other ignored native hooks. Ignored SessionStart does not
claim a bound session.

For admitted hooks, SessionStart registers the session and SessionEnd checks
it out automatically. The agent does not need to call check-in/check-out.
An explicitly trusted adapter can also register a previously unseen native
session on its first allowed non-terminal hook. This covers out-of-order
delivery and enabling collection during an already open session. Existing
foreign or ambiguous bindings are not replaced; PF workers retain their
separate task/attempt authorization. Native lifecycle/message IDs stay
idempotent, including delayed SessionStart delivery.

Historical deferred payloads are not automatically discarded by changing this
setting. Operator-authorized maintenance must distinguish obsolete queued
sessions from current work and preserve required project history.


## Effective application configuration

`ConfigurationProvider` supplies the full immutable `PFConfig`, including metrics,
logging, temporary files, Garage hooks and database settings. It binds explicit
device/workplace/project paths and an already authorized typed `ProjectPFConfig`
context. It does not discover workplace enrollment or interpret Work permissions.
The host resolves routing before constructing it; no service or Runtime is needed.

Precedence is builtin → device → explicit selected workplace leaves → project →
authorized context. A workplace's missing fields inherit the device values.
Explicit false and explicit default-valued scalars override them. Project/context
null values inherit; their existing allowlist excludes metrics. Forge policy,
capsule scope and resource grants remain enforced independently of these settings.

```python
from processforge_core.configuration import ConfigurationProvider

# Paths below are absolute, authorized host inputs; construction performs no I/O.
live = ConfigurationProvider(
    device_path=device_path,
    workplace_path=selected_workplace_configuration,
    project_path=project_configuration,
    context_overrides=authorized_overrides,
)
snapshot = live.snapshot()  # one explicit application read per operation
configuration = ConfigurationProvider.pinned(snapshot.config, errors=snapshot.errors)
interval = configuration.get("runtime.metrics.interval_seconds")
driver = configuration.get("database.driver")
```

Consumers receive this pinned provider or its `current()` value; they do not read
or merge YAML themselves. Native worker snapshot transport, host builders, CLI
selection and other entrypoint composition belong to host integration. A worker's
application snapshot never grants policy or body-read access. No model prompt or
public lifecycle payload should receive private native snapshot metadata.

The provider selects the full device file when no device path is passed:
Windows `LOCALAPPDATA/ProcessForge/configuration.yaml` (home/AppData/Local fallback),
POSIX absolute `XDG_CONFIG_HOME/processforge/configuration.yaml` (home/.config
fallback). Relative environment roots are rejected. No directory scan, CWD-based
discovery, file creation, database open or daemon startup occurs on construction.
Missing selected files yield typed defaults; they stay absent on read.

`YamlConfigStore` obtains model, SHA256 revision and `ConfigSnapshot.explicit_keys`
from the same bounded validated bytes. Dotted scalar keys are leaves; each
`database.profiles.<id>` is atomic and each `database.defaults.<slot>` is a leaf.
Presence is internal metadata, never YAML. Device/workplace profiles must have
disjoint IDs, including identical duplicate definitions; project/context profiles
must be project scoped and cannot set workplace_main. Profile/default references
and scopes are validated. Paths remain relative to the authorized owner, never
the device-file directory. Profiles grant no filesystem or SQL access.

`snapshot(refresh=True)` rereads only the bound sources; normal snapshots check
file replacement signatures in the bounded synchronized resolver cache. First
invalid/unsafe reads raise the existing `ConfigurationError`. A later failed read
retains the last valid source together with its presence/revision and reports a
code in `ResolvedConfig.errors`. Merge/policy validation errors still raise.
Pinned refresh is a no-op returning the same snapshot; existing operations never
change after CRUD or another request. There is no mutable current-project global.

The old `resolve(base_path, project_path)` keeps its positional base/project
meaning. Low-level `resolve(None, project_path)` uses builtins. `project_path=None`
creates only an in-memory empty project snapshot; workplace selection is explicit.

`database.driver` accepts only sqlite or null/inherit and works without profiles.
`PFConfig.get("database.driver")` returns the operational sqlite default;
`ProjectPFConfig.get` returns an explicit selector or None. `with_changes` and
`ConfigService.reset` remove an explicit selector with None, preserving other
profiles/defaults. Absent database stays absent in serialized defaults and old
payloads. Existing CRUD still materializes the original fields as before; those
actually saved bytes count as explicit workplace overrides. Refresh cannot switch
an existing bound store UUID/path; that is a separate host maintenance decision.

An operation retains the selected device path separately from the pinned value.
Nested event, accounting and first-write hosts reuse the exact operation host or
its selector; a value-only pinned provider does not trigger device rediscovery.
The host revalidates actual project ownership, flow root, enrollment and target
routing at each migration safety boundary. These checks do not refresh or replace
the operation's PFConfig snapshot and grant no additional file access.
