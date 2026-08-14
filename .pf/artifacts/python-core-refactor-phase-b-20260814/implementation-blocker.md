# Phase B Implementation Blocker

## Status

The implementation has not started. No product source files were changed in Phase B.

## Blocking ownership

The existing assignment pre-release-remediation-implementation-20260730 is still in_progress and declares exclusive ownership of tools/**, including:

- tools/processforge.py
- tools/pf_runtime/mcp_server.py
- tools/pf_runtime/codex_hooks.py

The Phase B package/import slice necessarily changes the two runtime adapters, so ProcessForge correctly rejected the new implementation assignment for overlapping write scope.

## Live-process check

This is not a live daemon lock. The legacy worker runtime record is manual_required with no PID, no start time, and no heartbeat. The only observed Python processes are Serena MCP servers. The blocker is therefore stale declarative ownership in the legacy assignment.

## Prepared, reviewed implementation boundary

The Phase B specification and independent review agree on:

1. Create src/processforge_core/__init__.py and a stdlib-only bootstrap.py.
2. Preserve tools/processforge.py as the single legacy Core/CLI behavior source.
3. In direct-script adapters, retain only a minimal first-load shim for bootstrap.py; completely removing that shim would change the launch contract.
4. Centralize legacy-core loading and pf_runtime.host/service package imports inside bootstrap.py.
5. Reuse one legacy module object and bind the processforge module identity or verify that no name-based legacy imports remain.
6. Do not extract Process Definition, compatibility, event/work-state, transport, or worker-lifecycle semantics.

## Required resolution

Before creating a Phase B implementation worker, the owner of the legacy remediation assignment must either complete/release its tools/** scope or provide an explicit ProcessForge handoff that grants this bounded slice.

## Evidence

- package-bootstrap-spec.md
- package-bootstrap-spec-review.md
- .pf/assignments/pre-release-remediation-implementation-20260730.yaml
