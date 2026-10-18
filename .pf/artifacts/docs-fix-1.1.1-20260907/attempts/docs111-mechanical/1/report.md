# docs111-mechanical Report

- Date: 2026-09-07
- Assignment: `docs111-mechanical`
- Required outputs: `.pf/artifacts/docs-fix-1.1.1-20260907/docs111-mechanical-report.md`

### Files changed

- `docs/ru/concepts/resource-search-index.md`
- `docs/concepts/assignment-front-matter.md`
- `docs/validation/validation.md`

### What was changed

- D01 (`docs/ru/concepts/resource-search-index.md:76-80`)
  - Removed unsupported `--project-root <project>` from all 5 `search-index` CLI examples.
  - Kept `--workplace <workplace>` and existing command structure intact:
    - `search-index status --workplace <workplace>`
    - `search-index refresh --workplace <workplace>`
    - `search-index rebuild --workplace <workplace>`
    - `search-index doctor --workplace <workplace>`
    - `search-index tick --workplace <workplace>`

- D05 (`docs/concepts/assignment-front-matter.md`)
  - Updated `required_outputs` example from path list to mapping form:
    - `id: example-report`
    - `path: .pf/artifacts/example-report.md`
    - `type: markdown`
    - `required: true`

- D08 (`docs/validation/validation.md`)
  - Corrected checksum validator wording to match CLI behavior:
    - `--check` is the inventory comparison mode (default behavior when `--write` is not set).
    - `--write` writes/updates `checksums/processforge.sha256`.
    - Clarified it checks public file inventory only and does not validate context/capsule checksums.

### Exact checks/results

- `python tools/validate-process-forge-checksums.py -h`
  - Confirmed flags: `--root`, `--output`, `--write`, `--check`.
  - `--write` and `--check` are mutually exclusive; `--check` is compare.
- `python` parser validation via `build_parser` (executed with `PYTHONPATH` including `tools`)
  - Parsed all five revised commands above successfully.
  - Output ended with `OK_ALL True`.
- `git diff --check -- docs/ru/concepts/resource-search-index.md docs/concepts/assignment-front-matter.md docs/validation/validation.md`
  - No errors.

### Residual risks

- `tools/processforge.py` import of `build_parser` from this workspace required setting `PYTHONPATH=tools` in the validation command, because default import context does not include the module search path for `processforge_subprocess` by short import.  
- This is environmental, not a documentation change blocker; parser and docs outputs are now aligned with discovered CLI behavior.