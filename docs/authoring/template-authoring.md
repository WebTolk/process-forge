# Template Authoring

A reusable template must be stable enough to copy and adapt.

Template manifests should state:

- id
- version
- source package
- type
- compatible stages
- compatible platforms
- placeholders
- allowed modifications
- forbidden modifications
- post-copy instructions
- validation rules
- usage recording policy

Template bodies should keep placeholders explicit and avoid hidden local assumptions.

For workplace resource authoring, prefer the structured CLI:

```bash
python bin/pf.py template-create --workplace ./workplace --id report.audit.basic --title "Basic Audit Report" --apply
python bin/pf.py template-doctor --workplace ./workplace --template report.audit.basic
```

# Resource Management Template Rules

Template packages remain simple by default. A folder under `templates/file/<template-id>/` with a clear `README.md` is enough for MVP.

Add `template.yaml` only when metadata is needed. Do not put private absolute paths or secrets in template documentation or payload files.
