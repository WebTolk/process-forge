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
its mutable data. If long-lived PF processes are configured, arrange an operator
maintenance window before replacement, then start the intended new processes
after validation. File-only Garage needs no service installation.

With an updater-capable installation, plan against the downloaded archive and
inspect conflicts and the declared workplace migration before apply:

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

Existing non-empty legacy project event/raw-hook NDJSON journals require explicit
SQLite import before those journals can be used. This is separate from replacing
Core files or refreshing context. Follow [SQLite journal migration](../concepts/hook-journal-sqlite.md)
and the declared [migration tool](../../tools/migrate-hook-journals.py); retain the
originals and do not treat other NDJSON owners as obsolete.

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
