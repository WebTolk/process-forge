# Project Classifiers

Project classification is data-driven. ProcessForge inventories project paths,
loads active classifier documents from explicit registries, evaluates generic
`exists` conditions, and records the resulting project types, platforms, and
tags. Without an active matching classifier, the result is `unclassified` with
project type `unknown`.

Classifier documents conform to `schemas/project-classifier.schema.json`.
Registries conform to `schemas/project-classifier-registry.schema.json`.

```yaml
schema_version: 1
project_classifiers:
  - id: example.classifier.fixture
    path: project-classifiers/example.classifier.fixture.yaml
    status: active
```

Each rule uses either a non-empty `all` list or a non-empty `any` list. Its
`classify_as` object declares one or more opaque project type, platform, or tag
ids. Core attaches no meaning to those ids.

Workplace init and project onboarding create empty registries. An operator or
package installation flow must copy/import a classifier and add an active
registry entry. Package discovery alone never activates it.

An official bundled pack may provide classifier documents as data. They are
evaluated only when that pack is active or explicitly selected. For example, a
generic workplace does not attach meaning to `composer.json`; activating the
official software-development pack makes its classifier available without
adding any software-specific branch to the ProcessForge runtime.

When no active classifier matches but an inactive official pack has a matching
classifier, onboarding reports include an inactive classifier suggestion. This
is a hint to activate or import the pack intentionally; it is not automatic
classification and does not make core domain-aware.

Classification is persisted in the project-context snapshot and copied into a
context capsule. Changing a classifier, its registry, or a matching project
marker makes the current snapshot stale and requires context refresh.
