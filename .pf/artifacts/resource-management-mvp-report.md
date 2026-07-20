# Resource Management MVP Report

## Status

implemented

## Implemented

- Added proposal-first Resource Management CLI commands: `knowledge-add-url`, `knowledge-add-resource`, `knowledge-index-refresh`, `knowledge-package-doctor`, `docs-import-plan`, `template-add`, `tool-register`, `mcp-register`, and `platform-contract-install`.
- Added metadata-only resource indexes with `path_ref`, `load_policy`, `index_policy`, source, license, and update policy.
- Added workplace resource events under `runtime/events/events.ndjson` for knowledge, template, tool, MCP, and platform contract operations.
- Added seed processes for knowledge resource add, documentation mirror import, knowledge package update, template add, tool register, MCP register, platform contract install, and process template install.
- Added schemas, templates, concept docs, authoring docs, and a resource-management smoke runner.
- Extended `doctor-project` with knowledge resource index checks and kept public snapshot absolute-path checks.

## Manual Or Future Work

- Documentation import remains plan-only; no crawler or bulk downloader is enabled.
- Tool and MCP healthchecks are stored as metadata; no mandatory runner executes them.
- Multi-project snapshot invalidation is represented by events but not implemented as an automatic scheduler.
- Package registry discovery remains filesystem and registry-id based in the MVP.

## Example Command Flows

```bash
python tools/processforge.py knowledge-add-url --workplace <workplace-root> --package platform.example-parent --url <url> --kind article
python tools/processforge.py knowledge-add-resource --workplace <workplace-root> --package platform.example-parent --resource-file resource.yaml --apply
python tools/processforge.py knowledge-index-refresh --workplace <workplace-root> --package platform.example-parent --apply
python tools/processforge.py docs-import-plan --workplace <workplace-root> --source mdn --topics html,css,js
python tools/processforge.py template-add --workplace <workplace-root> --type file --id example-file-template --source <folder>
python tools/processforge.py tool-register --workplace <workplace-root> --id phpstan --capability php.static_analysis --command phpstan
python tools/processforge.py mcp-register --workplace <workplace-root> --id context7 --capability official_documentation --command context7
```

## Validation Results

- `python -m py_compile tools/processforge.py tools/smoke_resource_management.py`: PASS
- `python tools/validate-process-forge-schemas.py --root .`: PASS
- `python tools/validate-public-cleanliness.py --root .`: PASS
- `python tools/validate-process-forge-checksums.py --root . --check`: PASS
- `python tools/processforge.py events-validate --project-root .`: PASS
- `python tools/smoke_resource_management.py`: PASS
- `python tools/processforge.py doctor-project --project-root .`: PASS with existing bootstrap WARN items for missing project-init artifacts.

## Known Risks

- Resource availability checks validate registry ids and path_ref structure, not the availability of every external URL.
- Workplace runtime proposals/events are private runtime artifacts and are not included in release checksum inventory.
- Existing packages without resources do not produce indexes until resources are declared.
