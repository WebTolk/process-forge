# Documentation Import

Documentation import is plan-first in the MVP. ProcessForge does not crawl or download large sites silently.

`docs-import-plan` creates a documentation import plan with source, topics, license/source notes, proposed resource records, `load_policy`, and index policy. The plan can later be reviewed and used by a separate explicit mirror/import runner.

## Required Metadata

- source id
- topics
- license note
- update policy
- resource records with `path_ref`
- `load_policy: on_demand` for full documentation mirrors

## Non-goals

- no crawler by default
- no hidden network download
- no full documentation content in project snapshots
