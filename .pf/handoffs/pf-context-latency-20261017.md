# Handoff: context latency diagnosis

Read-only diagnosis completed; no product edits, history cleanup or Runtime/MCP restart. Exact Work selectors and terminal checksum are in .pf/artifacts/pf-context-latency-20261017/closeout.json. Terminal Work must not be resumed or its capsule changed.

Measured: unprofiled handler17.337s, CurrentWorkService.summary9.403s and automatic ProcessExecutionService.state6.632s, together92.484%. Source path builds complete Work histories twice before active filtering/selection. Repeat warm cache call had4hits,2689parses and2689evictions at64MiB; request cache8MiB was also full. cProfile43.538s is instrumented time, not ordinary latency.

Next bounded implementation: shared authoritative Work metadata projection, full bodies only for selected Work; preserve selection/ambiguity, pending completion recovery, ordering, current-byte/authority validation and response contracts. Report and public-summary contain facts; full profiles/scripts retained locally. Product fix needs new scoped Work and relevant contract checks.
