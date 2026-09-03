# ProcessForge Project Instructions

This project uses ProcessForge.

## Start Order

1. Read `.pf/START_AGENT_HERE.md` and `.pf/process-forge.yaml`.
2. Call `pf.context` with this project root. If MCP is unavailable, read the
   current snapshot as the file-only fallback.
3. Use `pf.search` when project-authorized knowledge is needed.
4. Use `pf.resolve` before opening a ProcessForge-managed resource root.
5. Call `pf.work.start` with the high-level objective when work becomes
   substantive. If it returns `process_choice_required`, select one offered
   process and call it again with `process_id`.
6. Call `pf.work.state` and follow the selected assignment and immutable
   capsule.
7. Satisfy the current stage obligations, then call `pf.work.transition` with
   an outcome and evidence. Never supply the next stage.
8. Repeat until PF returns `action: run_completed`.

## Important Rules

- Do not edit files outside assignment scope.
- Do not put absolute local paths into public files.
- Do not commit `.pf/process-forge.local.yaml`.
- Do not commit `.pf/runtime/`.
- Use project-local templates before global templates when allowed.
- Record template usage.
- Use low-level Run/Task lifecycle commands only for compatibility or
  diagnostics, not for the ordinary agent path.
- Do not commit `.pf/runtime/events/` or webhook outbox payloads.
- During ordinary project work, do not install, start, or repair PF Runtime,
  MCP, host hooks, or Agent Ledger. Use available PF tools and report an
  operator-level infrastructure blocker when PF requires operator action.
- A Work has one active process and its pinned active specializations. Follow a
  completed Work's handoff/next-work recommendation; do not combine process
  definitions into the current session context.
