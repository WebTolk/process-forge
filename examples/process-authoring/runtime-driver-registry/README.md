# Runtime Driver Registry Process Authoring Example

This example points to the public stable built-in `runtime-driver-registry` as a reference process pack.

- Process: `processes/core/runtime-driver-registry.yaml`
- Prompt: `prompts/runtime-driver-registry-agent.md`
- Documentation: `docs/processes/runtime-driver-registry.md`

Validate with:

```bash
python bin/pf.py process-doctor --project-root . --process runtime-driver-registry --contract-only
```
