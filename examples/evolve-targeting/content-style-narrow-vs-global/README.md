# Content Style: Narrow Versus Global

A content-production process may observe both project voice and reusable style
guidance. These are different targets.

## Narrow Project Rule

```yaml
target:
  type: project_rule
  id: project.content-voice
applicability:
  scope: project
  conditions:
    - Applies only to the current publication voice.
generalization:
  level: project_rule
promotion:
  status: not_requested
```

## Reusable Template Candidate

```yaml
target:
  type: template_package
  id: templates.example-content
applicability:
  scope: package
  applies_to:
    knowledge_packages:
      - templates.example-content
generalization:
  level: package_rule
routing:
  recommended_destination:
    type: template_package
    id: templates.example-content
```

Do not merge project voice and global style into one candidate. The narrower
candidate protects private or one-off editorial constraints from being promoted
as reusable policy.
