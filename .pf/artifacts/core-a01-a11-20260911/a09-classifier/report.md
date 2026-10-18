# A09 classifier repair report

## Result

Implemented stable classifier provenance for distribution-owned classifier files. Distribution-relative labels are now used, while project-local and workplace behavior is preserved.

## Changed files

- `tools/processforge.py`
- `tools/smoke_classifier_distribution_parity.py`

## Verification

- PASS - AST parsing.
- PASS - live-root check reports `packs/official/software-development/project-classifiers/software-web.yaml`.
- BLOCKED - smoke command hit Windows `PermissionError` (`WinError 5`) on disposable temp-directory creation. No workaround attempted per brief.

Run:

```text
python tools/smoke_classifier_distribution_parity.py
```

Classifier fingerprinting and stale detection remain intact.