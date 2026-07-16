# Workplace Resources

Workplace resources are reusable assets kept outside individual project `.pf/` folders.

Core resource groups:

- knowledge packages under authoritative package roots
- reusable templates under template roots
- platform contracts under platform contract roots
- registered tools and MCP providers

Projects select resources through workplace registries and platform contracts. Public project files store ids, relative paths, and snapshot summaries; they do not copy private local paths or heavyweight resource payloads.

Authoring commands emit events in `runtime/events/events.ndjson` so hooks and reviews can observe resource lifecycle changes.
