# Software Feature Development Process Authoring Example

This pack-local example accompanies the stable `software-feature-development`
process.

- Process: `packs/official/software-development/processes/software-feature-development.yaml`
- Prompt: `packs/official/software-development/prompts/software-feature-development-agent.md`
- Documentation: `packs/official/software-development/docs/processes/software-feature-development.md`

Use `lifecycle_mode: feature` for a local feature task, or `lifecycle_mode: full`
when delivery artifacts and the configured delivery profile are required. Activate
the pack and validate the contract before using either mode:

```bash
python bin/pf.py pack-activate --id processforge.official.software-development --workplace <workplace-root> --apply
python bin/pf.py process-doctor --project-root . --process software-feature-development --contract-only
```
