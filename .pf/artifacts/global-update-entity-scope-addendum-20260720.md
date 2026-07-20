# Addendum: Entity Update Scope For ProcessForge Updater

Date: 2026-07-20
Related run: `pf-global-update-design-20260720`
Status: planning addendum; no code changes

## Reason

The global ProcessForge updater must not be designed only as a mechanism for replacing the ProcessForge distribution archive.

The same update discovery and notification framework must also support updateable ProcessForge-managed entities:

- knowledge packages
- knowledge resources and local documentation mirrors
- process definitions
- reusable templates
- tool registrations
- MCP server registrations
- platform composition contracts
- package manifests that group any of the above

Project `.pf` migration remains a separate second layer. This addendum only expands the first/global updater design so that it can discover and report updates for multiple entity classes.

## Core Principle

Design one update discovery framework with typed update subjects.

`processforge_distribution` is one `subject_type`, not the whole model.

Recommended top-level normalized candidate identity:

```yaml
subject:
  type: processforge_distribution | knowledge_package | knowledge_resource | process_definition | template | tool | mcp_server | platform_contract | package
  id: processforge | docs.example | process.software-feature-development | template.project-context | tool.phpunit | mcp.playwright | platform.example-stack | package.process-forge-core
  scope: global | project
  current_version: "1.0.0"
  installed_from: source-id-or-local
```

## Registry Shape

Keep source registry generic. A source can publish distribution updates and entity updates in the same or separate manifests.

```yaml
schema_version: 1
product: processforge

sources:
  - id: official-processforge-releases
    enabled: true
    provider: github_releases
    priority: 10
    owner: ExampleOrg
    repo: process-forge
    subjects:
      - type: processforge_distribution
        ids: [processforge]

  - id: official-processforge-entity-index
    enabled: true
    provider: processforge_json
    priority: 20
    url: "https://updates.example.com/processforge/entities.json"
    subjects:
      - type: knowledge_package
        ids: ["*"]
      - type: process_definition
        ids: ["*"]
      - type: template
        ids: ["*"]
      - type: tool
        ids: ["*"]
      - type: mcp_server
        ids: ["*"]
      - type: platform_contract
        ids: ["*"]
      - type: package
        ids: ["*"]
```

The registry must live outside the replaceable distribution root, for example under the workplace root, so configured sources survive a ProcessForge distribution update.

## Normalized Entity Update Manifest

The custom JSON provider should support a generic entity manifest:

```json
{
  "schema_version": 1,
  "generated_at": "2026-07-20T00:00:00Z",
  "subjects": [
    {
      "type": "knowledge_package",
      "id": "docs.example",
      "name": "Example documentation package",
      "versions": [
        {
          "version": "1.2.0",
          "channels": ["stable"],
          "released_at": "2026-07-20T00:00:00Z",
          "stability": "stable",
          "compatibility": {
            "min_processforge": "1.0.0",
            "max_processforge": null,
            "schema_version": 1
          },
          "dependencies": [
            { "type": "knowledge_package", "id": "docs.parent", "constraint": "^1.0", "optional": false }
          ],
          "artifacts": [
            {
              "type": "full",
              "format": "zip",
              "url": "https://updates.example.com/processforge/entities/docs.example-1.2.0.zip",
              "sha256": "hex",
              "signature": {
                "type": "minisign",
                "url": "https://updates.example.com/processforge/entities/docs.example-1.2.0.zip.minisig",
                "key_id": "processforge-release"
              }
            }
          ],
          "changes": [
            { "type": "content", "summary": "Updated local documentation mirror snapshot.", "breaking": false }
          ],
          "migration": {
            "required": false,
            "guide_url": null
          }
        }
      ]
    }
  ]
}
```

The same shape applies to processes, templates, tools, MCP registrations, platform contracts, and packages. The meaning of `artifacts` differs by type, but discovery, verification, source priority, cache, notification, and approval boundaries remain shared.

## Subject-Specific Rules

### ProcessForge Distribution

- install is distribution replacement
- requires backup of distribution root
- requires `version`, `release-test` or equivalent validation, and `doctor-workplace`
- must not modify project `.pf` automatically

### Knowledge Packages

- updates may be metadata-only, content snapshot, local mirror, API snapshot, or archive replacement
- dependencies must be explicit
- provenance must be preserved
- large mirrors should support incremental manifests later, but full archive can be MVP
- project overrides must not be overwritten silently

### Knowledge Resources

- individual URL/API/file snapshots can update independently from the package
- must record source URL, fetched_at, checksum, and license/usage notes when available
- stale resources can trigger notification without forcing update

### Process Definitions

- process updates can add/remove/reorder stages
- breaking changes must be explicit because active project runs may depend on old stages
- installation should support side-by-side versions or pinning
- active project `.pf` should not be rewritten automatically

### Templates

- template updates affect future copies, not already copied project files
- notification should distinguish "template source updated" from "project file migration available"

### Tools

- tool registration update is not the same as installing the executable
- update candidate should describe command path policy, version detection command, expected outputs, and trust source
- execution/install of third-party tools requires separate approval

### MCP Server Registrations

- update can change command, args, environment variable names, capabilities, and approval policy
- secrets and tokens must remain outside public manifests
- enabling or changing MCP servers requires explicit operator approval

### Platform Composition Contracts

- platform contracts are compositions that attach packages of knowledge, tools, templates, MCP, and processes
- update candidate must include dependency graph and compatibility constraints
- composition updates must not leak concrete platform examples into core flow artifacts
- project-specific platform selection is still project layer; global updater only updates available contracts

### Packages

- package updates group multiple subject updates
- package install plan must show all included subject changes and dependency resolution
- partial failure must be recoverable or leave old versions active

## Cache And Notification

Candidate cache should key by:

```text
subject.type + subject.id + channel + version + source.id
```

Notification should group by subject:

- "ProcessForge distribution 1.0.1 available"
- "Knowledge package docs.example 1.2.0 available"
- "Template template.project-onboarding 1.1.0 available"
- "Platform contract platform.example-stack 2.0.0 available"

The orchestrator should notify at startup or scheduled intervals, but should not install automatically.

## Approval Boundary

Require operator approval for:

- updating the global distribution
- enabling or changing remote sources
- installing or updating executable tools
- enabling or changing MCP server registrations
- updating platform composition contracts
- applying any package update that changes more than metadata
- applying any update marked breaking
- applying updates to project-local `.pf`

Metadata-only updates can be discovered and reported automatically, but should still be operator-approved before changing persistent registries unless policy explicitly allows unattended metadata refresh.

## CLI Implication

Future CLI should avoid a distribution-only command tree. Prefer generic subject-aware commands:

```text
pf update sources --validate
pf update discover --scope global --subject-type all --channel stable --refresh
pf update candidates --subject-type knowledge_package
pf update download --subject-type knowledge_package --subject docs.example --version 1.2.0
pf update verify --package <path>
pf update install --subject-type processforge_distribution --subject processforge --version 1.0.1 --approve
pf update install --subject-type knowledge_package --subject docs.example --version 1.2.0 --approve
pf update notify --ack --subject-type template --subject template.project-onboarding --version 1.1.0
```

`self-update` can remain as a compatibility alias for `pf update ... --subject-type processforge_distribution --subject processforge`.

## Design Adjustment

The updater should be specified as:

1. generic update source registry
2. provider adapters
3. normalized typed candidate model
4. source health cache
5. candidate cache
6. notification state
7. package download and verification
8. subject-specific install planners
9. operator approval and rollback

This keeps the first layer broad enough for ProcessForge itself and for global ProcessForge-managed resources without mixing in project `.pf` migration.
