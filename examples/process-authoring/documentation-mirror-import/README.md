# Documentation Mirror Import Process Authoring Example

This example points to the public stable built-in `documentation-mirror-import` as a reference process pack.

- Process: `examples/domain-packs/content-workflow/processes/documentation-mirror-import.yaml`
- Prompt: `examples/domain-packs/content-workflow/prompts/documentation-mirror-import-agent.md`
- Documentation: `docs/processes/documentation-mirror-import.md`

Validate with:

```bash
python bin/pf.py process-doctor --project-root . --process documentation-mirror-import --contract-only
```
