# Hook collection and session lifecycle

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
