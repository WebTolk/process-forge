# Template Authoring

A reusable template must be stable enough to copy and adapt.

Template manifests should state:

- id
- title
- version
- kind or type
- compatible stages or processes when relevant
- compatible platforms when relevant
- placeholders
- allowed modifications
- forbidden modifications
- post-copy instructions
- validation rules
- usage recording policy

Template bodies should keep placeholders explicit and avoid hidden local
assumptions.

## Current CLI

For workplace resource authoring, prefer the structured CLI:

```bash
python bin/pf.py template-create --workplace ./workplace --id report.audit.basic --title "Basic Audit Report" --apply
python bin/pf.py template-doctor --workplace ./workplace --template report.audit.basic
```

`template-create` writes a reusable template under the selected workplace
template root. If no `--template-root` is supplied, the command uses the
registry/default root, normally `${PF_TEMPLATES}` / `reusable-templates`.
The command creates `template.yaml` and companion template files.

`template-add` is the proposal/copy command for registering an existing source
folder:

```bash
python bin/pf.py template-add --workplace ./workplace --type file --id <template-id> --source <source-folder> --apply
```

## Resource Management Template Rules

Template roots are selected through the workplace `templates` registry. Do not
assume a hardcoded `templates/file/<template-id>/` path for new authoring.

Do not put private absolute paths or secrets in template documentation or
payload files.
