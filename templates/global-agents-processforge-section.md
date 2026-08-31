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
2. Read the project flow entrypoint: `.pf/AGENTS.md`.
3. Read `.pf/process-forge.yaml`.
4. Call `pf.context` with the project root; use the current snapshot only as a
   file-only fallback when MCP is unavailable.
5. Use `pf.search`, `pf.resolve`, and `pf.work.start` as the normal high-level
   project path.
6. Never write secrets or local absolute paths to public files.
7. Follow assignment and immutable-capsule boundaries.
8. Do not install, start, or repair PF Runtime, MCP, host hooks, or Agent Ledger
   during ordinary project work; report operator-level infrastructure blockers.
<!-- PROCESSFORGE:END -->
