# Workplace Configuration

Use Workplace Init when setting up a machine or runner host for ProcessForge.

## Answers File

Start from:

```text
templates/workplace-init.answers.yaml
```

Set:

- workplace id
- workplace name
- type
- operating system
- root path
- optional knowledge roots
- optional package roots
- optional template roots
- optional tools root
- optional MCP root

## Apply

```bash
python bin/pf.py workplace-init --workplace <workplace-root> --apply
```

## Verify

```bash
python bin/pf.py doctor-workplace --root <workplace-root>
```

## Parameters

Workplace defaults for structured parameters can be declared directly in the
workplace answers/manifest or in the workplace parameter registry:

```text
<workplace-root>/registries/parameters.yaml
```

Use this for machine-local defaults that many projects may inherit: local test
stands, default publication channels, render presets, accounting profiles, or
any other domain-neutral parameter tree. ProcessForge stores and merges the
structure; it does not interpret the namespace.

Projects override these values through `.pf/process-forge.yaml`, private
`.pf/process-forge.local.yaml` `overrides.parameters`, `.pf/parameters.yaml`, or
`.pf/parameters.local.yaml`. The project context snapshot receives the computed
`resolved_parameters` tree and `parameter_resolution` provenance.

Do not write parameters in `AGENTS.md` expecting the resolver to parse them.
Markdown agent instructions are guidance. Machine parameters need an explicit
structured YAML or JSON source.

# Path Constants

Define reusable path bases in `workplace.yaml`:

```yaml
path_constants:
  PF_WORKPLACE: "."
  PF_KNOWLEDGE: "knowledge"
  PF_TEMPLATES: "reusable-templates"
  PF_TOOLS: "tools"
```

Registry entries may use `${PF_KNOWLEDGE}/joomla/docs` or an explicit absolute path. Absolute paths are allowed in workplace/private files, but never in public project snapshots.

Run `python bin/pf.py path-resolve --workplace <workplace-root> --path "${PF_KNOWLEDGE}/joomla/docs"` to inspect expansion.

## Package Roots

Configure package roots in `registries/package-roots.yaml`:

```yaml
package_roots:
  - id: global
    path: ${PF_WORKPLACE}/packages
    status: available
    writable: true
    default: true
```

Package roots control where Resource Management reads and writes knowledge
packages. If the registry contains more than one candidate for the same package
id, write commands require `--package-root <id>` to avoid updating the wrong
copy. `doctor-workplace` validates root ids, path constants, availability, and
writability.
