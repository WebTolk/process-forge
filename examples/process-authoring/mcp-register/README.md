# MCP Register Process Authoring Example

This example points to the public stable built-in `mcp-register` as a reference process pack.

- Process: `processes/mcp-register.yaml`
- Prompt: `prompts/mcp-register-agent.md`
- Documentation: `docs/processes/mcp-register.md`

Validate with:

```bash
python bin/pf.py process-doctor --project-root . --process mcp-register --contract-only
```
