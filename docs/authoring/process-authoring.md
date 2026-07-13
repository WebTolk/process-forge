# Process Authoring

A process definition describes repeatable work.

Required fields:

- `schema_version`
- `id`
- `name`
- `version`
- `status`
- `description`
- `stages`
- `roles`
- `required_capabilities`
- `artifact_definitions`
- `gates`
- `required_packages`
- `required_templates`
- `allowed_tools`
- `forbidden_actions`
- `evolution_policy`

Stages should state inputs, outputs, required role, allowed tools, exit gates, logging requirements, and handoff requirements.
