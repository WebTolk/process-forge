# Domain Model

## Entities

| Entity | Responsibility | Key attributes |
|---|---|---|
| HookConfiguration | Declares targets, event types, policies | id, type, enabled, path, event_types |
| RawHookJournal | Stores native provider receipts | raw_event_id, payload_hash, provider, session_id |
| ProcessEventJournal | Stores normalized project events | event_id, event_type, assignment_id, run_id, time |
| OutboxDelivery | Persistent hook payload file | delivery_id, target_id, event, chat, created_at |
| DeliveryResult | Outcome record of hook dispatch | delivery_id, status, exit_code, message |

## Relationships

- `HookConfiguration` → selects events for dispatch.
- `RawHookJournal` → `ProcessEventJournal` (normalization).
- `ProcessEventJournal` → `OutboxDelivery` (dispatch).
- `OutboxDelivery` → `DeliveryResult` (receipt).

## State transitions

1. Host emits native hook.
2. Adapter normalizes to PF event.
3. Journal persists event and queues dispatch.
4. Dispatcher writes outbox payload and result.
5. Work transition emits `process.stage.*` events following the same path.
