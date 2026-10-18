# Scope and acceptance

Fix repeated unchanged YAML parsing in long-lived Runtime/MCP and common document readers. Preserve actual-content freshness including same-size edits with restored mtime, deletion/recreation, safe parser/error/fallback behavior and independent mutable return objects. Bound memory for large/changing histories; no TTL-based permission/readiness assumptions or hidden persistent cache writes.

Measured starting owner: active_run_ids parses569 Run YAML files/16MB repeatedly; current Runtime9716 CPU18.587%/60s, current profile86.92% scheduler and49.55% Run discovery. Host37.8MB JSON is a separate remaining cost and must not be silently declared fixed by this YAML change.

Acceptance: shared-reader audit with explicit bypass/exception list; exact before/after discovery results and byte/loader/error behavior; warm scans avoid repeated parse and full-history copies, changed documents reparse on next read; bounded cache under growth/concurrent access; focused existing Work/Runtime checks and own review; exact clean dev archive/install/provenance and actual post-update CPU/profile. Retain residual Host JSON and connected-MCP limitations honestly. No general rewrite of Work storage or YAML formats, no deletion/rotation of historical Work, no unrelated process repair.
