# Workplace Resources

Workplace resources are reusable assets kept outside individual project `.pf/` folders.

Core resource groups:

- knowledge packages under authoritative package roots
- reusable templates under template roots
- platform contracts under platform contract roots
- registered tools and MCP providers
- explicitly registered project classifiers
- optional capability registries and `provides_capabilities` declarations on
  active resources

Projects select resources through workplace registries and platform contracts. Public project files store ids, relative paths, and snapshot summaries; they do not copy private local paths or heavyweight resource payloads.

Classifier registries are empty by default. An optional package becomes active
only after an operator or installation flow registers its resources.

Capabilities are workspace/project/package data. ProcessForge core does not
activate domain examples or provide software, web, media, legal, or other
domain capability ids by default.

Authoring commands emit events in `runtime/events/events.ndjson` so hooks and reviews can observe resource lifecycle changes.
