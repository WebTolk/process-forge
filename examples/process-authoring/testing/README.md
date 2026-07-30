# Testing Process Authoring Example

This example points to the official bundled
`processforge.official.verification` pack.

- Process: `packs/official/verification/processes/testing.yaml`
- Prompt: `packs/official/verification/prompts/testing-agent.md`
- Documentation: `packs/official/verification/docs/processes/testing.md`

Activate the official pack in the project's linked workplace, then validate:

```bash
python bin/pf.py pack-activate --id processforge.official.verification --workplace <workplace-root> --apply
python bin/pf.py process-doctor --project-root . --process testing --contract-only
```
