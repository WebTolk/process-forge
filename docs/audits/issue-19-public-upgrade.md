# Public 1.2.0 upgrade: Core files and project readiness

The external Core updater accepts the three public startup templates shipped in the installed 1.2.0 ownership manifest: .pf/AGENTS.md, .pf/hooks.yaml and .pf/process-forge.yaml. Their actual preimages or absence are retained before removal when the target no longer owns them. The exception applies only to the installed 1.2.0 manifest. New archives and other private/runtime paths retain the current exclusion policy.

The original defect was observable on the actual published ZIP: plan reported no blockers, but confirmed apply rejected those historical templates as private data. A release checkout or a small synthetic archive did not expose this mismatch. The focused tests cover removal, modified and missing preimages, unowned private siblings and refusal of private target payload.

## Reproducible component qualification

The Public Core upgrade workflow checks Windows and native Linux runners. It builds a clean candidate from the exact checked-out commit and downloads these immutable public assets:

- [ZIP](https://github.com/WebTolk/process-forge/releases/download/v1.2.0/processforge-1.2.0.zip): SHA256 0cd5c1f48ca0e94ddf5b0298b774a3498baf20e5a64b84dd9c05bbc0f36a2880.
- [Sidecar](https://github.com/WebTolk/process-forge/releases/download/v1.2.0/processforge-1.2.0.manifest.json): SHA256 2881c62ff279c9d418d7bb88ad01a321817c1c7454ec03e10227d3f6791d40bd.

The source recorded by public 1.2.0 is b70df739700f1559570f4b65481cd39616ccc1ea. The qualifier validates selected archive hashes, source commits, sidecars and every member before extraction or execution. Candidate commit/tree/hash and OS/Python/command results belong to the resulting receipt; the candidate is not a published stable release.

The workflow invokes tools/smoke_public_core_upgrade.py with explicit public assets, candidate ZIP/sidecar, expected candidate commit/hash, a new owned fixture root and a private evidence directory. It initializes the old Workplace/project once with public 1.2.0, creates a retained Work, then performs the external Core update. This initialization prepares the old test installation; it is not an update operation.

The component checks read-only planning, explicit confirmation, unchanged-release local edits and missing files, target payload convergence, real preimages/absence, unknown files, byte parity of project/Workplace state, and the retained Work's original identity/capsule checksum. Runtime-generated local state remains outside the release payload.

## Mandatory readiness remains separate

A successful Core replacement creates no native enrollment or old-writer retirement proof. In the reproduced never-enrolled public 1.2.0 project, subsequent storage apply, context refresh, new Work and worker preparation refuse storage_activity_unknown; execution inspection reports execution_activity_unknown. The current qualified historical cold-to-managed deployment is not supplied by this file-only route. See [execution authority](../concepts/execution-storage.md#first-cold-transition) and [ST12](issue-17-storage-paths.md).

The component receipt records project migration and worker-prepare results separately and explicitly sets full_t06_qualified to false. A green Core-files job cannot qualify SQL cutover, a native update route or successful worker start/status/collect. A configuration doctor and a readable old Work do not prove ordinary-write readiness. Missing/partial enrollment must continue to select or refuse its native route; file-only replacement cannot bypass it.

| Required outcome | Remaining qualification boundary |
| --- | --- |
| Existing storage migration | Qualified deployment authority, selected owner/routing/targets, old-writer exclusion, identity, pending/resume and final SQL authority |
| Worker after upgrade | Real finite prepare/start/status/collect after required migration succeeds |
| Core recovery | Actual failed/interrupted apply plus supported restoration or forward recovery; repair classification alone is insufficient |
| Registry restoration | The separate package-registry contract from issue18; it is not a Core or SQL rollback |
| SQL recovery | Verified snapshot/restore or forward recovery after cutover, preserving identity; no generic downgrade over new SQL commits |

Issue19/T06 remains open until all original Windows/Linux, native/storage, worker, recovery and independent-review criteria are satisfied. The existing exact1.1 Workplace migration is not a general 1.2-to-candidate migration chain. Repeated workplace-init, fresh project initialization, a legacy-write fallback or an invented retirement receipt cannot satisfy these requirements.
