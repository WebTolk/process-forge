# Orchestrator Shell Agents Minimal Example

This example shows a public, deterministic shell-agent workflow. It uses the neutral `test-shell-agent` runtime driver and simulated subagent report files.

Run it through:

```bash
python bin/pf.py orchestrator-shell-plan-create --project-root <project> --run orchestrated-work --title "Orchestrated work" --answers examples/orchestrator-shell-agents/minimal/orchestrator-shell-agent-plan.yaml --apply
python bin/pf.py orchestrator-shell-plan-validate --project-root <project> --run orchestrated-work
python bin/pf.py orchestrator-shell-plan-apply --project-root <project> --run orchestrated-work --apply
```
