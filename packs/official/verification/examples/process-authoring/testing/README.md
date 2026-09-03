# Testing Process Authoring Example

This pack-local example accompanies the stable `testing` process.

- Process: `packs/official/verification/processes/testing.yaml`
- Prompt: `packs/official/verification/prompts/testing-agent.md`
- Documentation: `packs/official/verification/docs/processes/testing.md`

Activate the pack in a linked workplace, then validate the process contract:

```bash
python bin/pf.py pack-activate --id processforge.official.verification --workplace <workplace-root> --apply
python bin/pf.py process-doctor --project-root . --process testing --contract-only
```
