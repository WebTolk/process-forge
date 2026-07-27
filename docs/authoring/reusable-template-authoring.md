# Reusable Template Authoring

`template-create` writes a reusable template folder under the selected template root and registers it in `registries/templates.yaml`.

```bash
python bin/pf.py template-create --workplace ./workplace --id report.audit.basic --title "Basic Audit Report" --apply
python bin/pf.py template-doctor --workplace ./workplace --template report.audit.basic
```

Created structure:

```text
reusable-templates/<template-id>/
|-- template.yaml
|-- README.md
|-- files/
|-- prompts/
|-- examples/
|-- tests/
|-- artifacts/
|-- reviews/
`-- handoffs/
```

The doctor checks the manifest, local absolute path safety, referenced payload files, and referenced prompts.

Template packages can declare `update_sites`. Use `manifest_url` and
`changelog_url`; run public cleanliness after template update authoring because
template examples and docs are release-visible.
