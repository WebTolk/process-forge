# ProcessForge Self Update

When a ProcessForge update changes resources used by a project context snapshot,
the updater does not rewrite the snapshot in place. It writes the update record,
marks impacted project snapshots stale, and leaves existing assignment capsules
pinned to their original snapshot id and checksum.

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

The newer `pf update ...` commands are now the unified updater MVP surface. They
validate global bootstrap update sources, derive installed entity update sites
from manifests and registries, read local override metadata, fetch
`processforge_json_file` / `processforge_json` manifests, write candidate and
notification caches, stage artifacts, verify sha256 and package identity, apply
supported local file-provider package/tool updates with `--confirm`, and roll
back from backups.

`installed-subjects.yaml` is local installed-state metadata. Scanned manifests
remain the primary source of update-site discovery; when an installed subject
record matches a scanned manifest, its version and update policy annotate the
derived update site record.

Self-update for the ProcessForge distribution remains conservative: check,
stage, and verify are safe paths, while applying over a source checkout requires
an explicit operator decision and may be documented as manual recovery instead
of an automatic overlay.
