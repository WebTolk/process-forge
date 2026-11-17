# Update System

Run these operator commands from the installed distribution root with the
Python environment selected during [installation](installation.md). Workplaces
and projects remain outside the replaceable Core directory. Ordinary project
agents must not update Core or repair optional infrastructure as a task workaround.

## Discover and review an update

The unified updater discovers servers and candidates, stages an artifact,
verifies it, and applies supported file-based updates after explicit confirmation:

```bash
python bin/pf.py update entity-sources rebuild --workplace <workplace>
python bin/pf.py update candidates refresh --workplace <workplace>
python bin/pf.py update candidates list --workplace <workplace>
python bin/pf.py update notifications list --workplace <workplace>
python bin/pf.py update changelog show --workplace <workplace> --candidate <candidate-id>
python bin/pf.py update stage --workplace <workplace> --candidate <candidate-id>
python bin/pf.py update verify --workplace <workplace> --candidate <candidate-id>
python bin/pf.py update apply --workplace <workplace> --candidate <candidate-id> --confirm
python bin/pf.py update rollback --workplace <workplace> --candidate <candidate-id>
```

Use `file:///` manifest/artifact URLs for deterministic local testing. Real
remote servers need HTTPS and trusted certificates, sha256 hashes, and review
of the release source and migration notes. See [requirements](../requirements.md).

## Update the installed Core

Do not unpack a release over a project's `.pf/`. Back up the installation and
its mutable data. In Garage, the operator stops PF and other writers before
replacement and restarts the intended version after validation. In Forge,
the updater owns that lifecycle for the single PF executor. File-only Garage
needs no service installation.

Extract the verified target archive outside the installed Core. Run the
following commands from that extracted distribution, retaining the original ZIP.
Inspect conflicts and the declared Workplace migration before apply:

```bash
python bin/pf.py core-update plan --core-root <installed-processforge> --archive <release-archive.zip> --workplace-root <workplace>
python bin/pf.py core-update apply --core-root <installed-processforge> --archive <release-archive.zip> --workplace-root <workplace> --confirm
python bin/pf.py core-update status --core-root <installed-processforge>
python bin/pf.py doctor-workplace --root <workplace>
```

The updater validates the archive's managed-file manifest, records backups and
an operation journal, and applies a matching archive-declared workplace
migration when one exists. The order is Core, then Workplace; do not run
independent workplace migrations concurrently. Existing user configuration is
not a reason to rerun `workplace-init`: that command is for initial setup.
For an interrupted operation, inspect `core-update status` and use the supported
`core-update repair` flow.

The older public 1.0.2 distribution has no manifest-based Core updater. Its
first managed transition uses the updater from an extracted target distribution,
with the same explicit installed Core and workplace targets. The original
[1.0.2 → 1.1.0 migration guide](../../updates/migrations/1.1.0-stable-release.md)
records that historical transition; its version-specific statements are not a
blanket migration promise for later releases. Keep project staging/scratch under
that project's `.pf/tmp/`, separate from the installation being replaced.

## Check each linked project

After Core and Workplace validation, assess each project with the installed CLI:

```bash
python bin/pf.py project-upgrade-check --project-root <project>
```

This writes `.pf/artifacts/processforge-update-assessment.md` using the installed
update index. It does not automatically migrate project configuration or prove
that journal data has been migrated. Read the assessment and the target release's
migration instructions before changing files.

Existing projects with legacy journals refuse ordinary writes with
`storage_migration_required`. New projects create SQL journals immediately;
they do not need an upgrade migration. With PF and writers stopped, run:

```bash
python bin/pf.py journal-maintenance import --project-root <project> --workplace <workplace> --apply
python tools/migrate-storage.py --project-root <project> --workplace-root <workplace> --apply --offline-confirmed --json
```

The first command imports event/raw-hook journals; the second imports execution
snapshots and binds supported stores to stable UUIDs. This is separate from Core
replacement and context refresh. For an interrupted second command, repeat its
exact roots with `--resume --offline-confirmed`. Preserve the original journals,
plans and backups. See [SQLite journal maintenance](../concepts/sqlite-journal-maintenance.md)
for checks, refusal states and recovery. Other NDJSON owners are not obsolete
merely because they use that format.

When required migrations are complete, refresh and check the current project:

```bash
python bin/pf.py project-context-refresh --project-root <project>
python bin/pf.py project-context-check --project-root <project>
python bin/pf.py doctor-project --project-root <project>
```

Existing assignment capsules stay pinned to their original context. A refresh
does not authorize silently rewriting or widening them. Resolve any required
handoff through the governed Work flow, and refresh resource indexes when their
status requires it. Inside a linked project use `python .pf/runtime/bin/pf.py`
instead of the distribution-relative launcher.
