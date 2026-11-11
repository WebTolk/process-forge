## Problem and result

Describe the concrete problem and resulting behavior. Link the issue or maintainer
request when available. State the selected task source (`local_pf` or `github`)
and link the issue when present. An intermediate PR must not close a larger task.

## Validation

List meaningful commands, tested revision/platforms, results and remaining limits.
For documentation-only changes, explain which execution checks do not apply.

## Contribution checklist

- [ ] This PR targets `dev`, or is an explicitly requested instruction backport to `main`, and contains a coherent change.
- [ ] I followed `CONTRIBUTING.md` and preserved unrelated work.
- [ ] No root project `.pf/`, credentials, local environment or private logs are included.
- [ ] Relevant checks and required Windows/Linux scenarios passed; limitations are explicit.
- [ ] Documentation and shipped checksums reflect the final change.
- [ ] Review findings have been addressed; pending acceptance is not claimed complete.

After merge: mirror the accepted target-branch commit to GitVerse and verify both refs.
