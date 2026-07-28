# Process Directory Layout Split Review

Result: pass

## Review Notes

- The change introduces a central resolver rather than adding new flat globs.
- Built-in process ids were preserved during the move to `processes/core/`.
- Generated processes now land in `processes/user/` by default.
- `process-template-install` was removed as pre-release catalog cleanup.
- Release policy now forbids real `processes/user/*.yaml` and `processes/custom/*.yaml` entries.

## Residual Risks

- Package-installed process roots remain an extension point; this slice reserves the model but does not implement a full package process registry.

## Verification

- Source public release-test passed with and without `--fail-fast`.
- Release archive test passed with full extracted public release-test.
- Public cleanliness, schema validation, checksum validation, and `git diff --check` passed.
