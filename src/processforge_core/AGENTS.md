# Core package layout

Apply these rules when adding or reorganizing code under `processforge_core`.
They describe source organization; PF Work grants and the pinned process still
govern access and execution.

## Placement

- Put new domain and application implementation modules in the package that owns
  their responsibility. Do not add more subject-prefixed implementation files to
  the Core root.
- Reuse the existing `work`, `configuration`, `process_catalog`, `egress` and
  `common` packages where their actual ownership fits. Create another package only
  for a coherent responsibility identified in the current architecture work.
- Keep the tree shallow. A package groups related modules; it is not a directory
  per class. Keep related errors, values and small helpers with their service when
  that makes the module cohesive.
- Root-level bootstrap, composition and shared API/dependency seams may remain at
  the root. Existing implementation files are migration work, not a precedent for
  placing new implementations there. Migrate further groups in bounded Work.
- Use `common` only for shared primitives used by multiple responsibilities, not
  as a miscellaneous bucket.

## Python conventions

- Use short lowercase package names, `snake_case.py` module names and `CapWords`
  class names. A module name describes its responsibility; it need not equal the
  name of one class. Avoid repeating the enclosing package name in every filename.
- Keep package `__init__.py` files minimal. Import from owning modules explicitly;
  do not introduce broad eager re-exports, import-time assembly or new loaders to
  disguise circular dependencies.
- Preserve existing explicit dependency injection and lazy composition. Directory
  structure alone does not require new classes, a DI container or new product rules.

## Refactoring and verification

- Before choosing structure, reread the PF-selected architectural inputs and local
  Python knowledge. Relevant resources are `docs.python`, `docs.python-practices`,
  `docs.python-peps` and, for package layout/delivery, `docs.python-packaging`.
  Record the concrete sources used; distinguish an external documentation check
  from material actually read through PF.
- During the current dev refactor, update all known consumers to canonical package
  imports and remove obsolete module files. Do not retain old import aliases,
  compatibility wrappers or a compatibility framework.
- Keep the existing algorithms, document formats, guards, locks and recovery unless
  the current task explicitly changes them. This package reorganization adds no
  functionality.
- Preserve the released external contract during the OOP refactor: CLI commands,
  options, exit codes, MCP tools and schemas, response/error payloads, published
  entrypoints and document/protocol formats. Internal module relocation must not
  rename, remove or add external operations. Check the existing interface inventory
  and affected consumers rather than inventing a new API.
- Update current ownership/import documentation and shipped checksum inventory
  when paths change. Preserve historical approved artifacts and immutable capsules.
- Use focused existing checks for affected imports and execution paths. Do not add
  a new test suite merely for moving files or for compatibility that is not retained.

See [Python Core Structure](../../docs/concepts/python-core-structure.md) for the
current ownership map and remaining migration boundaries.
