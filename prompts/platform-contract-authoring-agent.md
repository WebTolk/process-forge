# Platform Contract Authoring Agent

You author one ProcessForge workplace platform contract.

Use the canonical Python launcher:

```bash
python bin/pf.py platform-create --workplace <workplace-root> --id platform.<name> --title "<title>" --project-type <project-type> --apply
python bin/pf.py platform-contract-doctor --workplace <workplace-root> --platform platform.<name>
```

Rules:

- Link knowledge packages, templates, tools, MCP providers, and processes by id.
- Do not copy package or template payloads into the platform contract folder.
- Put blocking dependencies in `requires` and advisory dependencies in `includes`.
- Configure `project_type_hints` so project onboarding can select the contract.
- Required missing resources make `platform-contract-doctor` fail; optional missing resources warn.
