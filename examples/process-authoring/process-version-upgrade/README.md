# Process Version Upgrade Process Authoring Example

This example points to the public stable built-in `process-version-upgrade` as a reference process pack.

- Process: `processes/process-version-upgrade.yaml`
- Prompt: `prompts/process-version-upgrade-agent.md`
- Documentation: `docs/processes/process-version-upgrade.md`

Validate with:

```bash
python bin/pf.py process-doctor --project-root . --process process-version-upgrade --contract-only
```
