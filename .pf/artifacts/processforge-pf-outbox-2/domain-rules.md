# Domain Rules

## R1. Outbox is mandatory when enabled
If `.pf/hooks.yaml` defines an enabled outbox target matching the event type, `ProcessEventRecorder` must queue dispatch and `RuntimeHookDispatcher` must write the payload file.

## R2. Network delivery is opt-in
`network_send_enabled: false` means webhook targets are skipped; outbox remains the only active delivery mode unless explicitly enabled.

## R3. Session independence
Project outbox writing does not require an active host session; Work transitions from CLI/MCP also produce outbox payloads.

## R4. Immutability
Approved artifacts, capsules, and historical run records are immutable. Audit work may only read them and create new audit artifacts.

## R5. Evidence-first
Every stage transition must record artifact and gate evidence before the process advances.
