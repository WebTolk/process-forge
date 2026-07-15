# Path Resolution

ProcessForge resolves paths with a small Joomla-style model:

1. Read the raw path string.
2. Expand `${CONST}` from `workplace.yaml:path_constants`.
3. Accept absolute paths as absolute.
4. Resolve relative paths against the workplace root or explicit base directory.
5. Normalize separators for metadata and reports.
6. Return status metadata without writing private absolute paths to public project files.

Supported forms:

```text
${PF_KNOWLEDGE}/joomla/docs
D:/Knowledge/Joomla/docs
/srv/knowledge/joomla/docs
../relative/path
relative/path
```

Doctor checks fail on unknown or empty constants. Cyclic constant references are reported as failures.

When a user provides a new absolute resource path, Resource Management first tries to map it under existing roots. If no root matches, apply mode registers it in the workplace private resource path registry and public package/snapshot records use `path_ref`.
