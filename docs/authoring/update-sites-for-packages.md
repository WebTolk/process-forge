# Update Sites For Packages

Package, knowledge, template, tool, platform, process, and MCP manifests can declare `update_sites`. A public package update that changes behavior should include both `manifest_url` and `changelog_url`.

Use `processforge_json_file` for local mirrors and public smokes:

```yaml
id: acme.software-processes
type: process_package
version: 1.1.0
update_sites:
  - id: acme-main
    enabled: true
    provider: processforge_json_file
    manifest_url: "file:///mirror/acme-software-processes.json"
    changelog_url: "file:///mirror/acme-software-processes-changelog.md"
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
      backup_before_apply: true
```

Tool updates must declare an update policy. `replace_file` is supported for local file-provider smoke coverage. `custom_command_requires_confirmation` is documented as blocked by default and must not be used to run arbitrary remote scripts.

Local overrides live in `<workplace>/registries/update-site-overrides.yaml` and can disable a subject, replace `manifest_url`, change `channel`, pin a version, block major updates, or force manual apply.
