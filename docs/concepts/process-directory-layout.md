# Process Directory Layout

Process definitions are resolved by `id`; their file path is storage, not identity.

ProcessForge uses three process roots:

- `processes/core/`: built-in ProcessForge processes shipped with the distribution.
- `processes/user/`: processes authored locally through process authoring or by hand.
- `processes/custom/`: imported, migrated, brownfield-normalized, or otherwise non-standard local processes.

`processes/user/` is the default write target for `process-create` and `process-authoring-apply`. Writing into `processes/core/` is a maintainer action and requires an explicit core flag.

The resolver searches user/custom roots before core, keeps `process_id` stable across moves, and reports `origin`, `root`, `path`, and catalog role in `process-list`. Legacy flat files under `processes/*.yaml` are accepted only as a migration fallback and produce warnings.

Public release archives include `processes/core/**` and only placeholder files under `processes/user/` and `processes/custom/`. Real user/custom process definitions are private workspace or project state and are excluded from the public distribution.

Active manifests, docs, templates, examples, and package manifests should refer
to process files under `processes/core/`, `processes/user/`, or
`processes/custom/`. Flat process paths are migration-only.

This layout supports three primary scenarios:

- Greenfield first workspace: a new user starts from PF built-ins and authors new processes into `processes/user/`.
- Studio workstation provisioning: a clean machine installs known packages and resolves shipped core processes without recreating them.
- Brownfield normalization: existing AGENTS.md files, snippets, skill packs, and scattered docs can be imported into `processes/custom/` or formalized into user processes.
