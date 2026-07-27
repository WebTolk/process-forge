# Reusable Templates

A reusable template is a reviewed starting point for an artifact, manifest, process definition, or handoff.

Templates do not execute actions. Tools execute actions.

## Template Manifest Fields

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

## Usage Tracking

Whenever a template is used, record:

- template id and version
- source package
- target files
- substitutions
- modifications summary
- validation result
- actor
- timestamp

## Updates

Reusable template packages can declare `update_sites` with `manifest_url` and
`changelog_url`. Template updates can modify package manifests, template files,
examples, and docs. Public cleanliness remains required before release.
