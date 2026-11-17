# Core Update Manifest

ProcessForge core updates use an explicit ownership manifest:

```text
processforge-core.manifest.json
```

The release archive contains the new manifest. An installed core root stores the currently installed manifest at the root of the distribution directory. The manifest is the boundary for PF-owned files.

## Manifest contract

Minimum fields:

- `schema_version: 1`
- `kind: processforge.core_manifest`
- `version`
- `generated_at`
- `source`
- `files[]`
  - `relative_path`
  - `size`
  - `sha256`

Paths must be relative to the core root. Absolute paths, backslashes, empty segments, `.`, `..`, and paths escaping the core root are rejected.

`runtime/`, workplace data, project `.pf` data, caches, SQLite indexes, and update journals are derived/local state and should not be modeled as core-owned payload files.

## Update flow

The CLI surface is:

```bash
python bin/pf.py core-update status --core-root <core>
python bin/pf.py core-update plan --core-root <core> --archive <processforge.zip>
python bin/pf.py core-update apply --core-root <core> --archive <processforge.zip> --confirm
python bin/pf.py core-update repair --core-root <core>
```

`plan` is read-only. `apply` requires `--confirm`.

### Existing file-only installations

For an existing installation without native enrollment, extract the verified
development/release ZIP outside the installed Core and run that archive's
`bin/pf.py core-update plan|apply` with the installed target and original ZIP.
Use the explicit Workplace root when the installation serves one. Stop its
known App Server first; explicit Windows `server stop --force` from the external
archive can recover an authenticated exact owner that rejects shutdown.

The file updater retains backups, progress/failure journals, private data and
manifest-last verification. It refuses overlapping installer/target roots,
unknown native-enrollment state and Workplace migration operations. Any native
markers, including partial enrollment, keep the target on its qualified native
update route. The file updater creates no native authority and does not claim
that its cooperating-writer mutex fences every independently running host.

Public 1.2.0 shipped three Core-owned startup templates under its own .pf/:
AGENTS.md, hooks.yaml and process-forge.yaml. The external file updater retains
their actual preimages or absence before removing old-only paths. This historical
allowance applies only to the installed 1.2.0 manifest; new archives still exclude
private .pf data. Core replacement does not establish project migration authority.
See the [public upgrade qualification boundary](../audits/issue-19-public-upgrade.md).

## Compatible Workplace Migration

An archive may carry a declarative Workplace migration under
`updates/migrations/`. For an existing Workplace, include its root in the same
Core-update transaction:

```text
python bin/pf.py core-update plan --core-root <core> --archive <processforge.zip> --workplace-root <workplace>
python bin/pf.py core-update apply --core-root <core> --archive <processforge.zip> --workplace-root <workplace> --confirm
```

The plan lists only archive-declared operations. Apply is serial: it replaces
the Core files and writes the Core manifest first, then applies the compatible
Workplace migration. Project `.pf` changes are assessed and applied later,
inside each project's own governed work. Concurrent independent Core or
Workplace applies are unsupported.

The 1.0.2-to-1.1.0 migration
adds the built-in `codex-exec` driver and its registry entry only when missing;
existing files and registry entries are preserved. It does not invoke
`workplace-init`, which remains a first-time initialization command.

Before a migration write, the updater copies the affected Workplace files into
the Core update backup directory and records the operation in the update
journal. When the post-Core Workplace migration cannot finish, the Core remains
at its new manifest and `core-update repair` reports a manual-repair state with
the backup location. A successful apply automatically runs the short
`doctor-workplace` check and stores its result in `last-apply.json`.

The updater computes:

```text
removed = old_manifest.files - new_manifest.files
added   = new_manifest.files - old_manifest.files
changed = common paths with different sha256
```

Only paths present in the old manifest and absent from the new manifest are deleted. Unknown files are preserved. Directories are removed only when they become empty.

PF owns the release-owned Core payload. A confirmed update must bring all such
files to the qualified target release bytes, replacing local Core edits even
when the official bytes did not change between releases. The manifest
differences above therefore do not limit which Core files need replacement.

Existing public flags remain accepted. Force is not required solely for local
Core edits and does not bypass authority, ownership, selection, path, collision
or safety checks. Unknown non-owned files, configuration, project and Workplace
data, and runtime state retain their existing handling. This replacement policy
does not authorize deleting user data.

The new installed manifest is written last, after file changes have succeeded.

## Recovery

Apply writes runtime update state under:

```text
<core>/runtime/core-update/
```

Before replacing or removing old PF-owned files, the existing recovery backup
preserves their actual pre-update bytes, including local edits, and records
absence for missing files. If an update is interrupted or a file operation fails,
`core-update status` reports `incomplete_update`, and `core-update repair` reports
the incomplete state for operator handling.

File operation failures, including locked-file style failures surfaced by the OS, are converted into explicit `file_operation_failed` errors and leave `runtime/core-update/in-progress.json` with `status: failed`.

The incomplete update journal records:

- installed and target versions;
- update archive;
- backup directory;
- counts;
- completed operations;
- pending operations;
- backed-up files;
- failure code/message when available.

`core-update repair` classifies incomplete states as:

- `safe_to_rollback` when the update failed before manifest write and the old manifest backup is present;
- `manual_repair_required` when the manifest was already written, the journal is incomplete, or safety cannot be proven;
- `nothing_to_repair` when no incomplete update exists.

The default repair command and the Python `repair_status` API remain read-only.
The classification alone does not authorize recovery. A new file-only apply
pins the original archive, old/new manifests, saved plan, actual preimage hashes
and lengths, and initial absence of added paths before any payload mutation.

For a failed or interrupted **before-manifest file-only** update made by this
updater, stop the selected Workplace App Server, release the filesystem fault,
and use the same external sealed installer and original archive:

```sh
python installer/bin/pf.py core-update repair --core-root CORE --resume --archive ORIGINAL.zip --workplace-root WORKPLACE --confirm
```

Repeat the original explicit Workplace selection; omit it only when the original
apply omitted it. Without confirmation, no recovery writes occur. Recovery uses
the same cooperating file mutex, unmanaged target, nonoverlap and offline guards.
It checks target/Workplace identity, all pinned control and backup bytes, and
current touched files against proven initial or exact intended bytes. An
operation interrupted after replacement but before journal publication can be
completed idempotently from those bytes. Progress counters alone grant nothing.

Recovery continues the original plan without replanning around the incomplete
update blocker. It preserves original backups, update identity and failure
history, retains the prior journal for each admitted recovery attempt, verifies
all target-owned bytes, and publishes the manifest last. Another failure retains
the incomplete journal and evidence. Unknown files remain preserved.

Old journals without versioned proof, incomplete/corrupt backups, drift, wrong
archive or bindings, native/partial enrollment, and any after-manifest state
refuse this route. Ordinary apply still refuses incomplete updates. This command
does not roll back files, adopt native installations, change SQL bindings or
downgrade Core after SQL commits; those states require their own supported
maintenance procedure.

## Original-manager bridge qualification boundary

The Windows original-manager source bridge is restricted to a genuine public
1.2.0 installation controlled by its original trusted launcher before its first
writer. Its Core owner is `OriginalManagerUpdateService`; the native adapter
retains the original gate, sentinel and complete Job set. A finite issuer-bound
profile pins the unchanged old ZIP/sidecar, physical roots, protected runtime
closure, environment and exact argv for all six ingress classes. The source
does not provide a public option to assert or reconstruct this profile.

The fixed manager route calls the existing plan/apply/confirmed repair contracts
from a separate accepted current installation. It uses the existing owned-file
delta, pins actual preimages and absence, and refuses active configuration/data
overlap with Core. Only the three exact historical 1.2.0 entry templates may be
backed up/removed; new payloads cannot claim private ownership. File-only update
continues to refuse every complete or partial managed marker.

Before copying, the original manager publishes a permanent replacement intent.
The native adapter backs up owned preimages, copies atomically and publishes the
manifest last. It then uses the existing legacy-manager pending/guard/epoch/bound/
head handoff. The new child captures the accepted new publication under its own
lease, invokes the existing storage coordinator and checks the SQL execution
repository. The old parent performs no subsequent Core imports or storage writes.

Copy/adoption recovery requires the exact retained operation, archive, selection,
preimages, physical bindings and journal in the same live manager. A receipt
cannot recover lost original handles. Manager loss before bound, an uncertain
child outcome, substituted roots/guards, corrupt backups and foreign selection
refuse automatic replay. Preserve history and backups. Once SQL has committed,
use its supported forward recovery; this bridge does not authorize downgrade.

If intent/control publication fails before the first journal, the same live
manager revalidates original payload and completes only its retained control
bytes and the physical backup directory it created. Conflicting control bytes
or a substituted directory refuse. This does not reconstruct a manager from
files or permit replay after an uncertain child outcome.

This is an implementation/qualification boundary, not a statement that the full
public upgrade has passed. Positive public-archive migration/worker, actual
copy-failure recovery, independent review and applicable OS qualification remain
required. A later manager cannot qualify an installation with unknown historical
writers. This Windows slice adds no Linux controller or historical cold route.
