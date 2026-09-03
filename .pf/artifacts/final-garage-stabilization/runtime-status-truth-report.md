# Runtime Status Truth Report

Date: 2026-08-24
Status: ready_for_implementation

## Finding

Runtime status payloads expose historical runtime implementation fields such as
`runtime_version` next to the installed PF core version. This can be read as the
current installed product version.

## Minimal Fix

Keep compatibility fields, but add explicit truth-shaped fields:

```yaml
installed_pf:
  version: <current PF version>
runtime:
  running: true|false
last_runtime_instance:
  version: <runtime implementation version>
  status: current|historical|not_available
```

Stopped or stale runtime state must not be represented as the installed PF
version.
