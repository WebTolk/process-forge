# Event storage scaling risk

Status: recorded technical debt; no database redesign proposed.

## Current model

`RawIngressKernel` writes private raw records into hourly NDJSON shards under `runtime/agent-events/raw/v1/YYYY/MM/DD/HH.ndjson`. It serializes ingress with an exclusive ingress lock, serializes each shard append with a shard lock, fsyncs the append, and writes one JSON index per `raw_event_id` plus, when available, one per stable native identity. A crash between append and index causes a full raw-shard scan to rebuild the missing index. Explicit stale-lock recovery is available; live locks are not removed automatically.

## Risks

- Index cardinality grows as one or two small files per raw event.
- Recovery scans all raw shards rather than a bounded time/index window.
- A single ingress lock serializes all writers at the workplace level.
- Raw payloads larger than 1,048,576 canonical JSON bytes are rejected before storage; they are not replaced with a receipt or external blob reference.

## Deferred direction

First measure real workload before changing storage. A future small design may consider compacted indexes, bounded recovery checkpoints, and an oversized-payload receipt plus private blob spill. This task must not introduce a new database, queue, or blob subsystem without a separate architecture decision.
