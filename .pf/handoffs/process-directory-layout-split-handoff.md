# Process Directory Layout Split Handoff

Status: ready

## Changed Contract

Process definitions are resolved by `process_id` through root-aware discovery. The shipped product catalog lives in `processes/core/`; locally authored definitions live in `processes/user/`; imported or brownfield-normalized definitions live in `processes/custom/`.

## Operator Notes

- Use `python bin/pf.py process-list --project-root . --origin core` to list built-ins.
- Use `python bin/pf.py process-layout-doctor --root .` to validate the layout.
- Use `python bin/pf.py process-create --project-root <project-root> --answers <answers.yaml> --apply` to create a user process.

## Verification

Full source and extracted-archive release validation passed. The built archive contains 677 public files and excludes real `processes/user/` and `processes/custom/` process definitions.
