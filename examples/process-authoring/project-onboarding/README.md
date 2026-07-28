# Project Onboarding Process Authoring Example

This example points to the public stable built-in `project-onboarding` as a reference process pack.

- Process: `processes/core/project-onboarding.yaml`
- Prompt: `prompts/project-onboarding-agent.md`
- Documentation: `docs/processes/project-onboarding.md`

Validate with:

```bash
python bin/pf.py process-doctor --project-root . --process project-onboarding --contract-only
```
