# Platform Version Selection Design

Status: ready_for_review

## Contract

Project manifests may set `context_requirements.resource_selection`:

```yaml
platform_versions:
  platform-id: "6.1"
```

Explicit `knowledge_resources` selectors take precedence and support `id`,
`preferred_version`, `constraint`, and `required`. Selection is generic: no
platform name is hard-coded in ProcessForge core.

## Compatibility And Fallback

An explicit selector chooses the greatest candidate satisfying its constraint,
preferring an exact requested version when present. A legacy manifest without
selectors derives target major/minor versions from direct package identities,
keeps direct package resources, and selects only the greatest compatible
version for each logical resource id. It never falls back to every available
resource.

## Indexing

Legacy selected documentation is migrated to bounded full-text indexing over
Markdown, text, and reStructuredText. `source_tree` and `symbols` legacy
policies are metadata-only, preventing accidental source corpus expansion.
