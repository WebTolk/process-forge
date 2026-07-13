# Local Supervisor Protocol Draft

The MVP does not require a runner. This draft reserves a future file protocol for local supervisor mode.

## Modes

- `manual`: humans or agents read and write files directly.
- `local_supervisor`: a local process reads assignments and coordinates jobs.
- `managed`: a future external control plane reads and syncs files.

## Runtime Layout

```text
runtime/
  queue/
    ready/
    running/
    submitted/
    completed/
    failed/
  events/
  locks/
  agents/
  supervisor.log
```

## Future Runner Responsibilities

- read assignments
- create execution contexts
- start agents or humans
- track timeouts
- collect logs and artifacts
- write events
- work without requiring an external backend
