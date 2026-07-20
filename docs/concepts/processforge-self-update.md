# ProcessForge Self Update

ProcessForge is a versioned product. Linked projects can keep their own `.pf/`
artifacts while the shared ProcessForge distribution is updated separately.

The MVP update model is file-first:

- the distribution contains `updates/processforge-update-index.yaml`
- migration guides live under `updates/migrations/`
- `self-update-check` reads only the distribution-local update index
- `project-upgrade-check` writes `.pf/artifacts/processforge-update-assessment.md`
- no project files are modified automatically

The assessment records installed version, available version, channel, breaking
changes, required migrations, affected files, manual review needs, recommended
steps, and rollback notes.

The newer `pf update ...` commands are a separate read-only framework surface.
They validate global bootstrap update sources, derive installed entity update
sites from installed manifests, read local override metadata, and validate
normalized update manifest fixtures. This surface does not fetch network
manifests, merge candidates, download artifacts, install packages, roll back
transactions, or migrate project `.pf` directories yet.

`installed-subjects.yaml` is treated as local installed-state metadata for the
future install/discovery layers. In the current read-only slice, scanned
manifests remain the source of update-site discovery; when an installed subject
record matches a scanned manifest, its version can annotate the derived update
site record. Subjects that exist only in `installed-subjects.yaml` do not yet
participate in update checks because no install/discovery mechanics have been
implemented for them.

Network update discovery, candidate caches, downloads, verification, automatic
migration execution, rollback, notification scheduling, and WTAICC scheduling
are future integrations.
