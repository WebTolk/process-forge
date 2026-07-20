# Path Resolution

ProcessForge resolves paths with a small registry-based model:

1. Read the raw path string.
2. Expand `${CONST}` from `workplace.yaml:path_constants`.
3. Accept absolute paths as absolute.
4. Resolve relative paths against the workplace root or explicit base directory.
5. Normalize separators for metadata and reports.
6. Return status metadata without writing private absolute paths to public project files.

Supported forms:

```text
${PF_KNOWLEDGE}/example/docs
<knowledge-root>/example/docs
<shared-knowledge-root>/example/docs
../relative/path
relative/path
```

Doctor checks fail on unknown or empty constants. Cyclic constant references are reported as failures.

When a user provides a new absolute resource path, Resource Management first tries to map it under existing roots. If no root matches, apply mode registers it in the workplace private resource path registry and public package/snapshot records use `path_ref`.

## Package Roots

`registries/package-roots.yaml` is the authoritative resolver for package
manifests and package resource indexes. A package command resolves the selected
root by `--package-root <id>` or by the default package root. Unknown root ids
fail. A selected root with a missing path warns in dry-run and fails in apply.

The legacy `<workplace-root>/packages` fallback is only used when the package
root registry is missing or empty, and commands report that fallback as a
warning. Public snapshots keep package root ids and `path_ref` records; they do
not expose resolved package root paths.
