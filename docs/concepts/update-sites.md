# Update Sites

Update sites are the ProcessForge contract for discovering new versions of
installed subjects. They are intentionally file-first and can run without a
daemon, database, web UI, or real network in tests.

An update-able subject declares one or more `update_sites` entries:

```yaml
update_sites:
  - id: vendor-main
    enabled: true
    manifest_url: "file:///mirror/acme-processes.json"
    changelog_url: "file:///mirror/acme-processes-changelog.md"
    channel: stable
    priority: 10
    trust:
      require_https: false
      require_sha256: true
      allow_unsigned: true
      signature_required: false
    policy:
      check_interval_hours: 24
      auto_check: true
      auto_stage: false
      auto_apply: false
      notify_operator: true
      notify_director_inbox: true
```

`manifest_url` points to the update manifest. `changelog_url` points to the
human-readable change log. The manifest may be a local file, as in the example
above, or a remote HTTP(S) URL. ProcessForge chooses the read path from the URL
itself; operators do not need to declare a source type.

Public smokes use local `file:///` manifests and artifacts so tests stay
deterministic.

Supported installed subject types include `processforge_distribution`, `workplace`, `process_package`, `knowledge_package`, `template_package`, `tool_package`, `tool_definition`, `platform_contract`, `mcp_definition`, `process_definition`, `reusable_template`, and `knowledge_resource`. `project_pf` is assessment-only and is excluded from normal downloadable update candidates.

## Evolve Package Releases

The common evolve learning loop does not bypass update sites. A knowledge hub
release writes a local update manifest for a reviewed package version.
Workplaces then use the normal `update candidates refresh`, `update stage`,
`update verify`, and `update apply` commands.

Unreviewed candidates and generated learning bundles are not public archive
content. Only reviewed package releases and update manifests are distributed.
