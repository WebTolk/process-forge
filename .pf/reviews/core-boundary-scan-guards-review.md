# Core Boundary Scan Guards Review

Result: pass.

Reviewed:

- Role-aware path guards are centralized in core helpers.
- `doctor-project` protects PF-looking roots unless project type is explicit.
- Project-local package index warning is narrowed to avoid false positives.
- Platform snapshots distinguish available contracts from selected stack.
- `platform-create` keeps legacy args compatible as optional aliases.
- New smokes cover all requested acceptance categories.

Residual risks:

- Existing Russian docs contain older mixed RU/EN wording; new RU concept pages
  cover the new boundary contracts without rewriting unrelated content.
- Role-aware source inventory is exposed as core helper and doctor behavior, not
  as a dedicated end-user CLI.
