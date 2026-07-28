# Testing Process Authoring Example

This example points to the public stable built-in `testing` as a reference process pack.

- Process: `processes/core/testing.yaml`
- Prompt: `prompts/testing-agent.md`
- Documentation: `docs/processes/testing.md`

Validate with:

```bash
python bin/pf.py process-doctor --project-root . --process testing --contract-only
```
