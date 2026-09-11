# D02 D03 D04 D07: Garage workflow and evidence

You are a bounded PF shell worker explicitly requested by the operator. The orchestrator owns Run/Task lifecycle and .pf state: do NOT call pf.work.start/transition, session-start, task-complete, update manifest/capsules, start infrastructure, or delegate. Read your assignment capsule and this brief; no full-project bootstrap is needed. Use apply_patch for edits; read UTF-8 explicitly on PowerShell. Preserve all existing unrelated changes, especially tools/processforge.py and the required-output fix. Write only assigned files; do not change VERSION, CHANGELOG, checksums or publish/install/update anything. No network research is needed: current local source is authority. Repository temp dirs only .pf/tmp/. Return a complete Markdown report as your final response, with timestamp, files changed, exact checks/results and residual risks; the launcher captures it as expected report. Do not claim completion on mere file existence.

## Assignment

Implement D02/D03/D04/D07 from audit. Canonical ordinary path context -> work.start(objective, optional process_id) -> work.state -> do obligations -> work.transition(outcome,evidence,notes) until run_completed. Multiple allowed processes require explicit choice from process_choice_required candidates; default is recommendation; active Work remains pinned. No manual Ledger session or lifecycle for ordinary agents. Keep low-level commands only clearly qualified compatibility/operator examples; if keeping English two-task example, complete both tasks before run-complete. Add one complete concrete state/evidence example with artifact id/path, gate id/status passed, notes and recovery from rejected missing evidence; ids must come from state and semantic attestation must not be fabricated. Differentiate artifact file existence vs semantic review. Include terminal behavior. Add new concept links from both indexes (RU may explicitly link EN reference, do not create unnecessary full translations). Keep EN/RU consistent and preserve operator initialization and advanced orchestration material. Read current process_execution.py and mcp_server.py sections listed in audit plus templates/project-agents-template.md, templates/process-agent-prompt.md, garage-core.md. Do not edit product logic. Run focused docs smokes (no full release-test).

## Allowed product writes

- prompts/task-batch-execution-agent.md
- docs/getting-started/task-batch-workflow.md
- docs/ru/getting-started/task-batch-workflow.md
- docs/concepts/runtime-mcp.md
- docs/ru/concepts/runtime-mcp.md
- docs/getting-started/agent-prompts.md
- docs/ru/getting-started/agent-prompts.md
- docs/concepts/declarative-process-execution.md
- docs/index.md
- docs/ru/index.md

