# ProcessForge Self Update

ProcessForge is a versioned product. Linked projects can keep their own `.pf/`
artifacts while the shared ProcessForge distribution is updated separately.

The MVP update model is file-first:

- the distribution contains `updates/processforge-update-index.yaml`
- migration guides live under `updates/migrations/`
- `self-update-check` reads the distribution update index
- `project-upgrade-check` writes `.pf/artifacts/processforge-update-assessment.md`
- no project files are modified automatically

The assessment records current version, available version, channel, breaking
changes, required migrations, affected files, manual review needs, recommended
steps, and rollback notes.

Network update servers, automatic migration execution, and WTAICC scheduling are
future integrations.
