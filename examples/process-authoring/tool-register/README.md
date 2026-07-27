# Tool Register Process Authoring Example

This example points to the public stable built-in `tool-register` as a reference process pack.

- Process: `processes/tool-register.yaml`
- Prompt: `prompts/tool-register-agent.md`
- Documentation: `docs/processes/tool-register.md`

Validate with:

```bash
python bin/pf.py process-doctor --project-root . --process tool-register --contract-only
```
