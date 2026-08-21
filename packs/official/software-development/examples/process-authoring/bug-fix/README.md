# Bug Fix Process Authoring Example

This pack-local example accompanies the stable `bug-fix` process.

- Process: `packs/official/software-development/processes/bug-fix.yaml`
- Prompt: `packs/official/software-development/prompts/bug-fix-agent.md`
- Documentation: `packs/official/software-development/docs/processes/bug-fix.md`

Activate the pack in a linked workplace, then validate the process contract:

```bash
python bin/pf.py pack-activate --id processforge.official.software-development --workplace <workplace-root> --apply
python bin/pf.py process-doctor --project-root . --process bug-fix --contract-only
```
