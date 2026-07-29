# Project Overrides

Project overrides are project-local refinements of workspace resources. They
live under `.pf`, normally in `.pf/project-overrides.yaml`, and can point to
project-local override files.

Supported override modes are `overlay`, `extension`, `replace`,
`parameterize`, `disable`, and `fork`. The MVP resolver records every applied
override, applies `disable` to activated resources, and calculates an effective
fingerprint from the base resource hash, override hash, and merge mode.

Project overrides do not mutate workplace resources. The resolved context for
one project can disable or parameterize a tool, template, MCP provider,
knowledge package, or specialization while another project using the same
workspace remains unaffected.

Snapshots record applied overrides and fingerprints. Capsules receive only the
activated resource summary and project override summary, not full raw knowledge
or override content.

Overrides refine the active resource profile for one project. They do not
change the process execution route, stages, acceptance criteria, or evidence
requirements.
