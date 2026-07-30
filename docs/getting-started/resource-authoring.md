# Resource Authoring

Resource authoring creates reusable workplace assets before they are selected by projects.

The MVP includes three authoring processes:

- `reusable-template-authoring`
- `knowledge-package-authoring`
- `platform-contract-authoring`

Use the Python launcher from this checkout:

```bash
python bin/pf.py template-create --workplace ./workplace --id report.audit.basic --title "Basic Audit Report" --apply
python bin/pf.py knowledge-package-create --workplace ./workplace --id docs.example-domain --title "Example Domain Documentation" --package-root global --apply
python bin/pf.py platform-create --workplace ./workplace --id platform.example-app --title "Example Application Platform" --project-type example-app --requires-package docs.example-domain --optional-template report.audit.basic --apply
```

Inside an onboarded project, use the project-local launcher:

```bash
python .pf/runtime/bin/pf.py project-context-refresh --project-root .
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

Project onboarding reads `project_type_hints` from platform contracts. When a contract declares a matching hint, the project context snapshot records the selected platform, linked knowledge packages, and linked templates without copying their payloads into the project.

Create resources dependency-first:

1. Configure path constants and `knowledge_roots.local-docs`.
2. Register tools and MCP servers.
3. Create or import knowledge packages.
4. Create reusable templates.
5. Create platform contracts that reference those resources.
6. Onboard projects so `project-onboard` can write `platform_stack` and inherited `knowledge_stack`.

Do not create platform contracts first if their required packages, templates, or tools do not exist yet.

Base languages and web technologies are modeled as knowledge packages and
capabilities, not as platform contracts. This keeps platform inheritance focused
on real application or domain dependencies while still allowing each platform
contract to include the base knowledge packages it needs.
