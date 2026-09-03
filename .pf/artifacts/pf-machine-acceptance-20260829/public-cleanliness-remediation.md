# Public Cleanliness Remediation

Status: pass

## Confirmed blockers

- A public Garage smoke embedded two machine-local Windows paths.
- The same smoke embedded concrete platform knowledge package ids.
- Three fixture smokes used the local variable name `docs`, which the public
  domain-neutral scanner correctly treated as a possible `docs.*` package id.

## Changes

- Replaced the machine-dependent article/source smoke with a portable temporary
  fulltext and source-tree fixture.
- Replaced platform-specific resource identities with fixture identities.
- Renamed ambiguous local variables to `knowledge_root` without behavioral
  changes.
- Kept real Joomla knowledge verification outside the public release suite as a
  machine acceptance task.

## Verification

- All four affected Garage smokes pass.
- Python compilation passes.
- `validate-public-cleanliness.py` passes.

## Boundary

This remediation proves the portable release contract only. It does not replace
the later real-machine Joomla MCP/search and browser acceptance.
