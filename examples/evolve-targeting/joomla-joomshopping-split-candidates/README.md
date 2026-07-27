# Split Candidates For Parent/Child Platform Work

This example uses public placeholder ids even though the folder name mirrors a
real-world parent/child platform scenario.

## Observation

A run on `platform.example-child` found two separate learnings:

- The child platform needs an additional packaging check.
- The delivery command should be documented for the project release profile.

## Correct Candidate Split

Candidate A stays with the child knowledge package:

```yaml
source_context:
  platform_stack:
    - platform.example-parent
    - platform.example-child
target:
  type: knowledge_package
  id: docs.example-child
applicability:
  scope: platform
  applies_to:
    platforms:
      - platform.example-child
  inheritance:
    observed_on:
      - platform.example-child
    parent_platforms:
      - platform.example-parent
    safe_for_parent: false
generalization:
  level: narrow_observation
routing:
  recommended_destination:
    type: knowledge_package
    id: docs.example-child
promotion:
  status: not_requested
```

Candidate B targets the delivery profile:

```yaml
target:
  type: delivery_profile
  id: project.default_delivery
applicability:
  scope: project
generalization:
  level: project_rule
```

The hub must not place Candidate A in `docs.example-parent` just because the
source stack contains `platform.example-parent`.
