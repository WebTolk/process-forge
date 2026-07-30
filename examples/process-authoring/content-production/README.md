# Content Production Process Authoring Example

This example points to the official bundled
`processforge.official.content-workflow` pack.

- Process: `packs/official/content-workflow/processes/content-production.yaml`
- Prompt: `packs/official/content-workflow/prompts/content-production-agent.md`
- Documentation: `packs/official/content-workflow/docs/processes/content-production.md`

Activate the official pack in the project's linked workplace, then validate:

```bash
python bin/pf.py pack-activate --id processforge.official.content-workflow --workplace <workplace-root> --apply
python bin/pf.py process-doctor --project-root . --process content-production --contract-only
```
