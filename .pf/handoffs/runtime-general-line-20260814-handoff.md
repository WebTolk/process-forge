# Handoff: Runtime correctness -> next Runtime slice

Objective:
Continue the PF Runtime general-line master prompt without duplicating PF Core.

Current status:
The first Runtime correctness slice is complete and targeted release-test proof passes.

Files changed:
- `tools/pf_runtime/host.py`
- `tools/pf_runtime/service.py`
- `tools/smoke_runtime_host_poc.py`
- `tools/smoke_long_lived_runtime.py`
- `.pf/artifacts/runtime-general-line-20260814/**`

Verified:
- session-to-project `/event` denial;
- concurrent Runtime cache writes;
- unresponsive/PID-reuse-like stale recovery;
- deterministic Windows oversized-request rejection;
- targeted Runtime release-test.

Files not to touch without a new assignment:
- unrelated PF Core lifecycle and historical release work;
- checksum inventory and release archive.

Known issues:
- `project-context-check` remains blocked by classification/capability resolution;
- Runtime session cache has not yet been reduced in favour of Ledger-first restore;
- full release remains blocked by stale checksum inventory.

Next recommended action:
Run the separate context-unblock slice, then implement Ledger-centric session routing and restart restoration before a live Codex hook adapter.
