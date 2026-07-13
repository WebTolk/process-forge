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
