# Generic Child-To-Parent Promotion

This example shows how a child-platform observation becomes a parent-platform
candidate without becoming a parent rule automatically.

## Parent Candidate

```yaml
source_context:
  platform_stack:
    - platform.example-parent
    - platform.example-child
target:
  type: knowledge_package
  id: docs.example-parent
applicability:
  scope: parent_platform
  applies_to:
    platforms:
      - platform.example-parent
  inheritance:
    observed_on:
      - platform.example-child
    parent_platforms:
      - platform.example-parent
    safe_for_parent: false
generalization:
  level: parent_platform_candidate
  promotion_requires:
    - Evidence from another child platform or parent implementation.
  confidence_for_promotion: low
routing:
  recommended_destination:
    type: knowledge_package
    id: docs.example-parent
promotion:
  status: proposed
  target:
    type: knowledge_package
    id: docs.example-parent
  blockers:
    - Needs broader evidence.
```

`knowledge-package-build-from-candidates --package docs.example-parent` stages
this item in `resources/incoming-learnings.md` until promotion is approved.
