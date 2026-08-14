# Phase D integration — classification and metadata convergence

## Delivered boundary

Phase D removes the remaining duplicate Process Definition classification/metadata implementation from the legacy CLI.

- `src/processforge_core.process_catalog` now publicly exports `PROCESS_CATALOG_CLASSIFICATIONS` and `process_catalog_metadata`.
- `tools/processforge.py` imports those symbols only through the package root.
- Legacy names remain as a compatibility constant alias and a thin `process_catalog_metadata()` wrapper, so validation and reporting callers retain their names, results and user-visible checks.
- `process_is_public_stable()`, `validate_process_contract()` and `builtin_process_catalog_report()` remain CLI policy/reporting code and were not moved.

## Deliberately excluded

No change was made to catalog/resolve helper adapters, authoring validation, runtime state/event, MCP, hooks or launcher/bootstrap behavior.

## Quality disposition

- Spark inventory and `gpt-5.4` design established the bounded slice.
- Independent design review required package-root exports rather than direct `service` imports.
- Applied diff passed compile, direct CLI and bin help, constant identity and metadata parity checks.
- Initial post-change review raised a FAIL about pre-existing direct private-helper calls used by the Phase C catalog/resolve bridge. Independent `gpt-5.4` adjudication determined this is residual adapter debt outside Phase D, not a regression or completion blocker.

## Residual follow-up

`tools/processforge.py` still uses `process_catalog_core` private helper calls for official/root adapter wrappers. Stabilize that catalog/resolve bridge in a later separately scoped phase; do not conflate it with classification/metadata convergence.
