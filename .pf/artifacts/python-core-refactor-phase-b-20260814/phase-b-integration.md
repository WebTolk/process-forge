# Python Core Refactor — Phase B Integration

## Delivered scope

Phase B establishes the reviewed package/import foundation without moving Process Definition, compatibility, event/work-state, transport, or worker-lifecycle semantics.

Changed product files:

- src/processforge_core/__init__.py
- src/processforge_core/bootstrap.py
- tools/pf_runtime/mcp_server.py
- tools/pf_runtime/codex_hooks.py
- tools/smoke_processforge_core_package_bootstrap.py

## Architecture result

The new bootstrap module centralizes:

1. Discovery of the repository root.
2. Importability of src and tools.
3. One cached legacy tools/processforge.py module object under both the internal and public processforge names.
4. Normal package imports of pf_runtime.host and pf_runtime.service.

The two direct-script adapters retain only their necessary first-load shim for bootstrap.py, then obtain their legacy Core and runtime modules from bootstrap_runtime.

## Worker chain

- Spark completed baseline and post-change characterization checks.
- gpt-5.4 completed architecture/specification, exact patch design, and independent implementation review.
- Two implementation attempts through the codex-exec worker were read-only despite their writable ProcessForge assignment. Their blocked reports are retained as runtime-driver evidence.
- The orchestrator applied the accepted gpt-5.4 unified diff through apply_patch, then ran smoke and independent review.

## Validation

- Dedicated package bootstrap smoke: pass.
- Python syntax compilation of the five product files: pass.
- bin/pf.py help and tools/processforge.py help: pass.
- MCP initialize and tools/list roundtrip through a Python subprocess: pass.
- Hook ignore outside a ProcessForge project: pass.
- Runtime status read only: pass; the pre-existing service status is stale and was not changed.
- All Phase B tasks pass task-doctor; run-doctor passes while active.
- git diff --check: pass.

## Residual conditions

- The minimal first-load shim in direct-script adapters is intentional. Removing it would require a launch-contract change beyond Phase B.
- Runtime start/stop and Windows detached-daemon lifecycle were not exercised because Phase B does not authorize changing runtime state.

## Next slice

Phase C may extract the shared Process Definition API for CLI, runtime host, MCP facade, and hooks. It must preserve the bootstrap seam and keep compatibility aliases outside canonical Core.
