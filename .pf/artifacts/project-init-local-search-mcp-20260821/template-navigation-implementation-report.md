# Template search and private navigation

## Delivered

- The snapshot producer now includes selected template records in
  `local_search_resources`, using a metadata-only concrete template `path_ref`.
- The `templates` registry alias now resolves concrete `templates` entries;
  `template_roots` remains the root collection.
- `pf.search` returns `local_path` only after it has matched a file inside a
  root resolved from the Ledger-bound project's fresh snapshot. This is a
  private runtime navigation value and is never stored in public snapshot
  artifacts.

## Fixture proof

The isolated stdio fixture creates and registers `joomla-plugin-manifest`,
adds it to the project context requirements, refreshes the snapshot and proves
that the producer emits a template record without workplace absolute paths.
It then searches `Joomla Plugin Manifest` through stdio MCP, receives a
template result and verifies that its private `local_path` exists. The fixture
retains knowledge scope, traversal, session mismatch, apply and public-report
checks.
