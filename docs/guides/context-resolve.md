# Read context without changing project files

`context-resolve` reads context. With no resource selectors it returns the
existing canonical project snapshot and its current freshness/readiness check:

```sh
python bin/pf.py context-resolve --project-root <project-root> --json
```

The output is one JSON object with `snapshot` and `check` fields. Without
`--json`, the same object is printed as YAML. The snapshot reader preserves
unknown fields. The check uses the same current policy and resource checks as
`project-context-check`; no refresh or index maintenance is implied.

Missing or broken snapshots return `snapshot: {}` and the existing broken check,
including `recommended_action`. The exit code is 1 for broken context or a
blocking policy, otherwise 0. A stale snapshot stays stale until an explicit
refresh. Missing project roots or PF manifests retain their existing CLI errors.

`--platform`, `--process` or `--specialization` selects the existing resource
resolution branch, which continues to return `resolved_context`. Its exit code
is 1 when `conflicts` is nonempty, otherwise 0. `--workplace` alone keeps the
snapshot/check branch and supplies the explicit workplace to its check.

## Explicit writes and legacy scripts

Refresh the modern project snapshot explicitly when needed:

```sh
python bin/pf.py project-context-refresh --project-root <project-root>
python bin/pf.py project-context-check --project-root <project-root> --json
```

Use `assignment-capsule` for a new modern assignment capsule. Existing capsules
keep their pinned inputs. `context-compile` remains a legacy explicit writer
with its existing prerequisites, including an existing legacy context index;
this repair does not convert it to the modern snapshot model.

Earlier versions of no-selector `context-resolve` unconditionally overwrote
`context-index.yaml`, `resolved-rules.yaml`, `context-conflict-report.md` and the
private `context-cache.yaml`, and ignored `--json`. That behavior is corrected.
Scripts relying on these side effects must migrate to the explicit modern
snapshot/capsule workflows; there is no implicit legacy-file regeneration.
The existing library writer `write_context_outputs` is unchanged.
