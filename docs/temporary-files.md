# Project temporary files

Put project scratch files under **`.pf/tmp/`**, using a separate subdirectory
for the current task. Keep durable results in `.pf/artifacts/` and handoffs in
`.pf/handoffs/`. This keeps disposable experiments out of the repository root.
Core includes this rule in the project instructions it generates.

Remove your own scratch when the task no longer needs it. Check that a worker
or unfinished operation is not using it, and retain any required evidence first.
The rule concerns project scratch; PF's established durable records and staging
files beside their destination for atomic replacement keep their existing roles.

## Old-file notifications

The optional app-server observes `.pf/tmp/` and reports files older than the
configured age. **The observer does not delete them.** Age identifies candidates for
review; it does not prove that a file is unnecessary. There is no search across
Work journals to guess which files are still useful.

Workplace settings live in `configuration.yaml`:

```yaml
schema_version: 1
runtime:
  temporary_files:
    mode: notify
    max_age_hours: 168
```

The defaults are `notify` and 168 hours (seven days). Set `mode: "off"` to disable
notifications; keep the quotes so YAML reads a string. The age accepts finite
numbers from 1 to 87600 hours. Preserve
the other sections when editing an existing configuration file.

A project's `.pf/configuration.yaml` can override either value. An omitted
value or `null` inherits the workplace setting. For example, to review candidates
after three days in one project:

If the workplace or project configuration file does not exist yet, create that
file first with the corresponding command below. The workplace and onboarded
project must already exist. Skip `create` for an existing configuration:

```bash
python bin/pf.py config create --workplace <workplace> --json
python bin/pf.py config create --workplace <workplace> --project-root <project> --json
```

```bash
python bin/pf.py config update --workplace <workplace> --project-root <project> --key runtime.temporary_files.max_age_hours --value 72
python bin/pf.py config read --workplace <workplace> --project-root <project> --key runtime.temporary_files.max_age_hours --json
```

Deleting an override restores inheritance:

```bash
python bin/pf.py config delete --workplace <workplace> --project-root <project> --key runtime.temporary_files.max_age_hours
```

## What an observation means

The app-server checks at most once per hour per project. It reads only a bounded
part of the local temporary directory and does not follow symlinks or junctions.
A missing directory is normal and is not created by observation.

The last result is kept privately under `.pf/runtime/maintenance/temporary-files.json`.
Context and status use the saved summary, without scanning scratch during a
context request. Partial coverage and stale or unknown results remain explicit;
counts may be lower bounds. A notification is not a complete disk inventory.

View the saved summary with:

```bash
python bin/pf.py project-context-check --project-root <project> --json
```

The result includes `temporary_files`. The agent's `pf.context` response includes
the same summary in `diagnostics`, with `code: temporary_files_status`.
These summaries do not expose candidate filenames. A report at least an hour
old, or made for different effective settings, is marked stale.

File-only work does not require an app-server and still follows the scratch
location rule. Without a running observer, do not expect a fresh background
notification. Start or configure infrastructure only through the operator's
chosen [Runtime workflow](getting-started/runtime-autostart.md).

## Permission to retain unused payload

`runtime.temporary_files.retain_unused` is an existing PFConfig leaf. Its global
default is `false`; a project accepts `true`, `false`, or `null` (inherit).
An explicit project `false` overrides global `true`. Composition remains builtin,
device, explicitly present workplace leaves, project, then authorized typed
project context. Strings and numbers are invalid booleans.

Only exact `true` in an error-free operation snapshot permits retention of unused
PF-owned payload. Last-valid values accompanied by current configuration errors
do not grant new permission. This setting grants no filesystem or Work rights.
Neither notification mode (`off` or `notify`) nor age authorizes retention or
deletion. Atomic sibling staging can always be discarded after its own use,
even when retaining other payload is permitted. Required input, recovery and
evidence remain needed until their actual consumers finish.


Ordinary prepared workers may receive an optional private `managed_scratch`
contract. Core allocates an exclusive new directory only under one literal,
immutable owned `.pf/tmp/?/**` write grant. Empty/read-only or ambiguous grants
allocate nothing. The contract adds no resource group or public CLI option;
native maintenance keeps its separate strict authority and material checks.
The prepared executor and Codex worker use the directory for `TEMP`, `TMP`,
`TMPDIR` and `PF_WORKER_SCRATCH`. Keep durable outputs, source and recovery data
outside this disposable namespace. A bounded private creation record is pinned
by the immutable prepared manifest; selected-attempt release/cleanup receipts
record real end of use and residual errors. Old unmanaged directories are not
adopted. Unknown child ownership blocks disposal and a new large attempt.

Owned directories use a bounded, identity-checked traversal without reparse
traversal. Cleanup runs after failed use and before retry, or after final
collection, outside admission/lifecycle locks and shutdown's active-only path.
Only an exact absent owned process tree and finalized durable evidence allow
release. Entry migration staging/probes are disposable once its durable journal
contains recovery inputs; the journal and needed recovery data remain.
