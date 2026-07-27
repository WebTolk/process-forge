# Update Sites

Update sites are the ProcessForge contract for discovering new versions of installed subjects. They are intentionally file-first and can run without a daemon, database, web UI, or real network in tests.

An update-able subject declares one or more `update_sites` entries:

```yaml
update_sites:
  - id: vendor-main
    enabled: true
    provider: processforge_json_file
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

`manifest_url` is the canonical field. Legacy `url` is accepted and migration-warned by the update-site validator. `changelog_url` should be present for public packages, templates, tools, processes, and knowledge updates that change behavior.

MVP provider support:

| Provider | Status | Capabilities |
| --- | --- | --- |
| `processforge_json_file` | implemented | fetch local manifest, copy local artifact |
| `processforge_json` | implemented | fetch HTTP/HTTPS manifest and artifact with timeouts |
| `generic_http_directory` | planned | schema name only |
| `github_releases` | planned | schema name only |
| `gitlab_releases` | planned | schema name only |
| `gitverse_releases` | planned | schema name only |
| `tuf_repository` | planned | schema name only |

Only implemented providers are claimed by smoke tests. Public smokes use local `file:///` manifests and artifacts.

Supported installed subject types include `processforge_distribution`, `workplace`, `process_package`, `knowledge_package`, `template_package`, `tool_package`, `tool_definition`, `platform_contract`, `mcp_definition`, `process_definition`, `reusable_template`, and `knowledge_resource`. `project_pf` is assessment-only and is excluded from normal downloadable update candidates.
