# Documentation Mirror Import Process Authoring Example

This example points to the stable `documentation-mirror-import` process from
the official bundled `processforge.official.content-workflow` pack.

- Process: `packs/official/content-workflow/processes/documentation-mirror-import.yaml`
- Prompt: `packs/official/content-workflow/prompts/documentation-mirror-import-agent.md`
- Documentation: `packs/official/content-workflow/docs/processes/documentation-mirror-import.md`

Activate the official pack in the project's linked workplace, then validate:

```bash
python bin/pf.py pack-activate --id processforge.official.content-workflow --workplace <workplace-root> --apply
python bin/pf.py process-doctor --project-root . --process documentation-mirror-import --contract-only
```
