# Platform Parity: platform-contract-example-parent

Result: `WARN`

## Checked

- source: `templates/platform-contract-example-parent.yaml`

## Skipped

- Full authoring round-trip for this resource type is not implemented in this MVP.

## Notes

- Platform contract is discoverable.
- Required and recommended resource references remain in the contract file.
- Referenced packages/templates are not copied into the contract.
- WARN: shallow parity check.

## WARN To Fix Before Public Release

- Replace shallow resource parity with a full authoring round-trip check.
