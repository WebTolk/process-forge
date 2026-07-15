# Path Constants

Path constants are workplace-local base paths used by registries and resource management commands.

Example:

```yaml
path_constants:
  PF_WORKPLACE: "."
  PF_KNOWLEDGE: "knowledge"
  PF_TEMPLATES: "reusable-templates"
  PF_TOOLS: "tools"
```

Relative constant values resolve against the workplace root. Absolute values are accepted as absolute in workplace/private files.

Public project files and public project snapshots must not contain resolved private absolute paths. They should expose `path_ref` records instead.

## Registry Use

```yaml
knowledge_roots:
  - id: joomla-docs
    path: "${PF_KNOWLEDGE}/joomla/docs"
```

Agents resolve the real path through the workplace manifest and registry. Projects receive only the registry id and optional relative path.
