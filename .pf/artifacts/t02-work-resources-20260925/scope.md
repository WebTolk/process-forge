# T02 Work resource reads — scope and context

Run: garage-t02-pf-vision-alignment-r02-implement-explicit-work-context-resou.
Assignment: t02-pf-vision-alignment-r02-implement-explicit-work-context-resource-sea.
Process: software-feature-development@1.1.0, pin cc411028e9585dd8f56e07faa8997d9e7af1a39a801a0d8c0ca9c8c1e89dfd49.
Snapshot: ctx-20260925-140110-0dbc7c, f73d8d332313f45a99d4e7b943e18bf4e812b44a51d4d8c682e8291b0753a562; actual connected pf.context fresh. Main capsule and assignment read; current Work has the two original project-local grants. Context is not refreshed.

Lifecycle: feature through all nine pinned stages, local source delivery. T08/T01/T09 completed and accepted. AFK operator authorizes the serial r02 plan and bounded junior-model delegation; the newer instruction documented in ../t01-work-contract-20260925/operator-coordination-override.md takes precedence over the older pinned single_agent restriction. Primary owns architecture, integration and transitions. Delegated writes will be disjoint and logged.

Goal: explicit work-search/work-resolve and pf.work.search/pf.work.resolve share one provider-neutral application service. Reads carry Work/context/resource generation and material provenance; grants are the intersection of pinned Work, current authorization and stage subset. Project navigation retains its existing meaning with an explicit scope marker. Detect changed/deleted/unavailable material, isolate two Works, preserve continuation and legacy capsules.

Acceptance: A->B selection never grants B to old Work A; revoke A blocks reads even from old cache; metadata/fulltext material versions are verifiable; missing stage subset inherits, empty grants none, expansion rejects; CLI/MCP selectors and semantics agree including session authorization; readiness/authorized coverage/resolution are separate; old capsules are unchanged and return an explicit unsupported legacy contract if proof is insufficient.

Allowed product scope: new src/processforge_core/work_resources.py; focused integrations src/processforge_core/{process_execution,garage,local_resource_search}.py, tools/processforge.py and tools/pf_runtime/mcp_server.py; additive resource-binding/context-capsule/process schemas as justified by architecture; new tools/smoke_work_resource_binding.py plus directly affected resource/Work regressions and standard release registry; relevant EN/RU context/search/runtime concepts and checksums. Private scope: this artifact directory, T02 log/handoff, normal PF-managed T02 state/evidence/projections and scratch .pf/tmp/t02-*.

Forbidden: installed/shared Core or registry changes, service operations, rewriting existing capsule or accepted plan/evidence, broad CLI refactor, T03 full capsule normalization, T04/T05 implementation, unrelated dirty work, public publication/push and T07/T10/local web UI.

Tool policy: attempted Serena get_symbols_overview for garage.py fails with Active languages: []; scoped rg/UTF-8 Python reads are the fallback. No platform is selected, no Python toolchain contract exists in the shared root (only PHP/JavaScript); use repository Python smoke/schema/public/checksum tools. Project-local .pf defines execution flow; no legacy global development-flow skills loaded.

Risks/unknowns for investigation: existing corpus is Workplace-wide and may not cover project-local grants; resource metadata schema and material generations may lack pin-ready fingerprints; legacy work must fail clearly rather than inherit current selection; current authorization must precede stale-cache access; mutable outputs cannot be treated as immutable fulltext inputs.
