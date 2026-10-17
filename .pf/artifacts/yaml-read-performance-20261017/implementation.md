# Implemented shared YAML parse reuse

Status: source implementation complete; actual installed delivery remains pending.

The shared document reader/request parser now uses one process-local, content-and-parser-policy-keyed bounded LRU. Every caller still reads current source contents. Independent snapshots preserve aliases/cycles and mutable isolation; unsafe/invalid YAML, custom stateful policies and unsupported/oversized snapshots retain existing behavior without shared retention. Existing request diagnostics count actual parsing and reuse. Runtime metrics adopts this owner after its existing file identity, containment, byte and time budget checks.

Run discovery selects id/status/__yaml_error__ only after a complete successful parse. Existing sorting, duplicate IDs, fallback IDs, status conversion and invalid-document skipping are preserved. The cache retains the small projection rather than growing Run history. No public CLI/MCP signature, file format or authority boundary changes; no new dependency.

Final frozen-corpus benchmark:570 unchanged Run files,16065514bytes,49 identical ordered active IDs; result SHA256ffdb1edcdec9be05cf4e7c740e8fec06e6ef21e63f6e38815fbb8205c4d3a40e. Baseline CPU4.546875/4.25/3.4375 seconds; candidate cold4.234375, warm0.15625/0.1875 seconds. Warm passes perform zero additional parses;570 retained entries have12117202 estimated bytes. Cold work and live-byte reading remain visible costs.

Focused source checks passed for request scope,12 new cache/freshness/policy/mutation/concurrency/error/retention/Run parity cases, project metadata/snapshot/Work composition, inventory, Runtime metrics/scheduler isolation/long-lived service, prepared execution, pinned capsule context, stage event emission and SQLite Runtime. Process catalog passed8 applicable tests; its retained-old-extraction comparison is explicitly skipped without the historical extraction fixture. The first catalog invocation omitted its required scratch argument; an attempted optional baseline pointed at an incompatible directory. These were invocation/fixture errors, corrected without product changes; the original initial error/results are retained.

Product paths and isolated source qualification are recorded separately. Private project configuration and unrelated repository state are excluded. Host JSON rewrite/read cost and actual connected MCP availability remain separate, previously measured residuals. No journal migration is repeated by this slice.
