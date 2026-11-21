# Update Lifecycle

The update lifecycle is explicit and operator-controlled:

1. `update entity-sources rebuild` derives installed update sites from subject manifests, installed subjects, registries, and overrides.
2. `update candidates refresh` fetches local/remote manifests, compares installed and available versions, writes `runtime/update/candidates.json`, and creates notifications.
3. `update changelog show` prints the candidate changelog URL and local changelog content for file-based manifests.
4. `update stage` copies or downloads the artifact into `runtime/update/staged/<candidate-id>/` and verifies sha256 when required.
5. `update verify` checks the staged artifact checksum and, for package zip artifacts, validates subject id/type/version from the package manifest.
6. `update apply --confirm` creates a backup, applies the local-file update for supported subject types, updates installed subjects, and writes an apply record.
7. `update rollback --candidate <id>` uses the recorded application and associated local backup to restore the package and its installed-subject metadata. The same ID works after candidate refresh and when the update source is unavailable.
8. `update doctor` validates update runtime caches.

`apply` never runs automatically. Tool updates with `custom_command_requires_confirmation` are blocked by default; ProcessForge does not execute arbitrary remote postinstall scripts.

Runtime state is not public archive content:

```text
runtime/update/candidates.json
runtime/update/notifications.json
runtime/update/staged/
runtime/update/applied/
runtime/update/backups/
runtime/update/rollbacks/
```

Keep applied records and their backups together for rollback. The staged record
can also be needed to recover an interrupted application or to determine the
payload type of an older update that created the destination.

Director inbox integration is optional. When a workplace has `director/inbox/`, update notifications can be mirrored as `type=update_available`; the CLI and files remain the canonical simple-mode notification path.
