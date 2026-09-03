# Specializations

Specialization is a workplace or project resource profile: it describes the
knowledge packages, tools, MCP providers, templates, and capabilities activated
for a specialist. It is not an agent profile, not a process, not a platform, and
not a mini-process.

ProcessForge core does not ship a required built-in specialization catalog and
runtime logic must not hardcode product, platform, tool, package, or role ids.
Operators create specializations after workplace initialization, after the
platform contracts, knowledge packages, tools, MCP providers, and templates they
reference already exist.

Specializations live outside the distribution root:

- `<workplace>/specializations/`
- `<workplace>/registries/specializations.yaml`
- `<project>/.pf/specializations/`
- `<project>/.pf/specializations/overrides/`

`platform_bindings` make one specialization platform-specific without turning it
into a platform. A selected platform stack can therefore resolve different tools,
knowledge packages, MCP providers, templates, and provided capabilities for
different specializations.

Specializations do not own workflow stages, gates, acceptance criteria,
required artifacts, or required evidence. Processes own those fields and express
abstract capability requirements. The resolver verifies whether the selected
specialization and platform binding provide those capabilities.

Project-allowed specializations are authorization, not an instruction to load
them all. A Work pins only its active specialization set; switching that set
requires a new Work/process boundary.

In 1.1.0 Work capsules pin the active process and active specialization set.
Resource authorization remains bounded by the project snapshot; further
process/specialization-specific resource narrowing is planned separately.

Capabilities are opaque ids from data. ProcessForge core does not ship a
software, web, content, media, legal, or other domain capability catalog, and it
does not satisfy specialization/process requirements with a built-in provider.
If the active specialization, activated resources, platform data, or project
overrides do not provide a required capability, the resolver reports it as
unsatisfied.

Examples in docs and smokes use `fixture.*` ids and are examples only.
