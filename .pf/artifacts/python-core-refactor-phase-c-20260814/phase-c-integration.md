# Phase C integration — shared Process Definition catalog API

## Delivered boundary

Phase C extracts the behavior-preserving catalog and resolver seam into `src/processforge_core` while keeping domain/runtime ownership stable.

- New core modules: `common/{ids,paths,yaml_io}.py` and `process_catalog/{models,service}.py`.
- `ProcessDefinitionRef` has one owner: `processforge_core.process_catalog.models`.
- `tools/processforge.py` remains the legacy CLI adapter. Its direct-script bootstrap adds `<repo>/src` before importing the core package, and legacy public functions delegate into the shared catalog API.
- `tools/pf_runtime/host.py::resolved_process()` builds a context from the legacy adapter, imports the seam lazily, and retains the existing mtime cache behavior.
- Runtime payload/state/event, MCP, hooks, authoring, validation, route and handoff code were intentionally not moved.

## Preserved contracts

- catalog ordering: user/custom roots, then `official` immediately before the first `core` root, then legacy-flat roots;
- classification and catalog-role rules, duplicate and strict warnings, declared override rules;
- official manifest, pack activation and inactive-official `pack-activate` diagnostic;
- YAML fallback parsing when PyYAML is unavailable;
- direct CLI and `bin/pf.py` import paths.

## Quality evidence

- Independent `gpt-5.4` design review: accepted the narrow boundary with explicit dependency/order conditions.
- The first patch design was rejected before application: it failed the direct CLI import prerequisite (`ModuleNotFoundError: processforge_core`). A corrective `gpt-5.4` design introduced the bounded CLI src bootstrap and lazy host import.
- Applied correction passed `py_compile`, direct CLI help, `bin/pf.py --help`, `ProcessDefinitionRef` identity check and `git diff --check`.
- Independent `gpt-5.4` code review: `PASS с условиями`; the remaining duplicate classification helper in validation/reporting is a future-drift concern, not a Phase C defect.
- `gpt-5.3-codex-spark` characterization passed compile and command checks. Its resolver smoke cannot create/delete temporary files because of ACL restrictions, even under `.pf/tmp`. Builtin catalog smoke has two pre-existing/contextual required-input failures unrelated to the catalog seam; details are in `smoke-retry.md`.

## Deferred work

Move the remaining validation/reporting classification helper only in a later, separately reviewed core-API phase. Do not infer that Phase C modularized the whole runtime host or bootstrap bridge.
