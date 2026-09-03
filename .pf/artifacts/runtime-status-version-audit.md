# Runtime Status Version Audit

Generated: 2026-08-24 12:00 +04

## Finding

`runtime status` delegates to `tools/pf_runtime/service.py`. The status payload
contains explicit version fields:

- `runtime_version: 1.0.0-poc`;
- `protocol_version: pf-runtime-poc-1`;
- `processforge_core_version: 1.0.2`.

The active checkout and CLI have moved beyond the original Runtime PoC naming,
but the Runtime service contract still reports PoC labels. This is truthful to
the constant currently used by the Runtime module, but it is a product clarity
gap for Garage users.

## Current Status Signal

The current workplace reports:

- `status: stopped`;
- `health: stopped`;
- historical `endpoint`, `pid`, `started_at`, and scheduler data from
  2026-08-14.

Consumers must prefer `status` and `health` over the mere presence of endpoint
or pid fields.

Status: `confirmed_product_clarity_gap`.
