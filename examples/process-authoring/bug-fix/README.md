# Bug Fix Process Authoring Example

This example points to the optional `software-web` domain pack.

- Process: `examples/domain-packs/software-web/processes/bug-fix.yaml`
- Prompt: `examples/domain-packs/software-web/prompts/bug-fix-agent.md`
- Documentation: `examples/domain-packs/software-web/docs/processes/bug-fix.md`

Validate with:

```bash
python bin/pf.py process-doctor --project-root . --process bug-fix --contract-only
```
