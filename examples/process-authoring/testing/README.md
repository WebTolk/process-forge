# Testing Process Authoring Example

This example points to the optional `verification-workflow` domain pack.

- Process: `examples/domain-packs/verification-workflow/processes/testing.yaml`
- Prompt: `examples/domain-packs/verification-workflow/prompts/testing-agent.md`
- Documentation: `examples/domain-packs/verification-workflow/docs/processes/testing.md`

Validate with:

```bash
python bin/pf.py process-doctor --project-root . --process testing --contract-only
```
