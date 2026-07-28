# ProcessForge Update Check Process Authoring Example

This example points to the public stable built-in `processforge-update-check` as a reference process pack.

- Process: `processes/core/processforge-update-check.yaml`
- Prompt: `prompts/processforge-update-check-agent.md`
- Documentation: `docs/processes/processforge-update-check.md`

Validate with:

```bash
python bin/pf.py process-doctor --project-root . --process processforge-update-check --contract-only
```
