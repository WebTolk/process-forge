# Architecture

## Audit architecture

```
+-------------+     +-------------------+     +------------------+
| Host agent  | --> | PF hook adapter   | --> | Runtime/Core     |
| (Kimi Code) |     | (kimi_hooks.py)   |     | (ProcessEventRecorder)
+-------------+     +-------------------+     +------------------+
                                                        |
                                                        v
                                              +------------------+
                                              | ProcessEventJournal
                                              | (SQLite events)
                                              +------------------+
                                                        |
                                                        v
                                              +------------------+
                                              | RuntimeHookDispatcher
                                              | (outbox writer)
                                              +------------------+
                                                        |
                                                        v
                                              +------------------+
                                              | .pf/runtime/hooks/outbox/
                                              +------------------+
```

## Components

- **HookConfigurationReader**: loads `.pf/hooks.yaml` and selects targets.
- **RawHookJournal**: persists provider receipts with deduplication/quarantine.
- **ProcessEventJournal**: persists normalized events and queues dispatch.
- **WorkEventPublisher**: emits process events during Work transitions.
- **RuntimeHookDispatcher**: writes outbox payloads and delivery results.

## Audit focus

- Verify that Work transitions and supervisor ticks produce outbox payloads.
- Verify that Kimi Code host hooks are registered and adapter is wired.
- Identify blockers for live host-hook verification.
