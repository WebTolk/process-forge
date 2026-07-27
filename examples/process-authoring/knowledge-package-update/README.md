# Knowledge Package Update Process Authoring Example

This example points to the public stable built-in `knowledge-package-update` as a reference process pack.

- Process: `processes/knowledge-package-update.yaml`
- Prompt: `prompts/knowledge-package-update-agent.md`
- Documentation: `docs/processes/knowledge-package-update.md`

Validate with:

```bash
python bin/pf.py process-doctor --project-root . --process knowledge-package-update --contract-only
```
