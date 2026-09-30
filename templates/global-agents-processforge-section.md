<!-- PROCESSFORGE:START -->
## ProcessForge

Apply this section when:
- the user mentions ProcessForge;
- the user says "по флоу";
- the user points to a `.pf/` directory;
- the project contains `.pf/process-forge.yaml`;
- an assignment references ProcessForge.

Rules:
1. Do not load all knowledge from this file.
2. Read root `AGENTS.md`; if absent in an unmigrated project, explicitly read
   `.pf/AGENTS.md`. This global navigation section is not delivery proof.
3. Read `.pf/process-forge.yaml`.
4. Call `pf.context` with the project root. If MCP is unavailable, use the
   existing CLI `project-context-check` and verified context fallback;
   a snapshot's presence alone does not prove freshness.
5. Use `pf.search`, `pf.resolve`, and `pf.work.start` as the normal high-level
   project path. Use returned Work/assignment/capsule IDs with `pf.work.state`
   and `pf.work.transition` until `run_completed`; handle `process_choice_required`.
6. Never write secrets or local absolute paths to public files.
7. Follow assignment and immutable-capsule boundaries.
8. Do not install, start, or repair PF Runtime, MCP, host hooks, or Agent Ledger
   during ordinary project work; report operator-level infrastructure blockers.
<!-- PROCESSFORGE:END -->
