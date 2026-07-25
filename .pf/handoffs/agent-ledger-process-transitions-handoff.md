# Handoff: implementation -> release/review

Objective:
Deliver Agent Ledger, Process Transitions, Agent Director, Continuation Capsule, and Orchestrator Shell Agents with Subagent Policy MVP.

Current status:
Implemented and validated. Public release archive was rebuilt and archive-tested.

Input artifacts:
- `задания/processforge_agent_ledger_process_transitions_shell_subagents_master_prompt.md`
- `.pf/artifacts/agent-ledger-process-transitions-report.md`
- `.pf/reviews/agent-ledger-process-transitions-review.md`

Files changed:
- `tools/processforge.py`
- `tools/test_agents/pf_shell_agent.py`
- `tools/smoke_agent_ledger.py`
- `tools/smoke_process_transition_handoff.py`
- `tools/smoke_agent_director_tick.py`
- `tools/smoke_orchestrator_shell_agents_with_subagent_policy.py`
- new schemas, templates, process definitions, prompts, docs, examples, and checksum inventory
- `dist/processforge.zip`
- `dist/processforge.manifest.json`

Files not to touch:
- `.pf/runtime/`
- `.pf/dogfooding/`
- private local machine paths

Known issues:
- `continuation-resume` is MVP partial and does not automatically execute the downstream process.

Required checks:
- `python bin/pf.py release-test --root . --public --timeout-scale 1`
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1`

Next recommended action:
Review the diff and, if accepted, commit the completed MVP slice.
