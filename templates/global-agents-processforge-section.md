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
4. Prefer `.pf/contexts/project-context.snapshot.md` if it exists.
5. If the snapshot is missing or stale, run/request project context refresh.
6. Never write secrets or local absolute paths to public files.
7. Follow assignment boundaries.
8. Write session telemetry when working inside ProcessForge.
<!-- PROCESSFORGE:END -->
