# Bug Fix Process Authoring Example

This example points to the official bundled
`processforge.official.software-development` pack.

- Process: `packs/official/software-development/processes/bug-fix.yaml`
- Prompt: `packs/official/software-development/prompts/bug-fix-agent.md`
- Documentation: `packs/official/software-development/docs/processes/bug-fix.md`

Activate the official pack in the project's linked workplace, then validate:

```bash
python bin/pf.py pack-activate --id processforge.official.software-development --workplace <workplace-root> --apply
python bin/pf.py process-doctor --project-root . --process bug-fix --contract-only
```
