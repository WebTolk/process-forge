# Knowledge Resource Navigation

Knowledge packages describe how agents should find reusable documentation,
snippets, local mirrors, API snapshots, examples, and standards without copying
heavy source trees into public package manifests.

Private local documentation and source snapshots must be referenced through
workplace knowledge roots.

```yaml
path_ref:
  registry: knowledge_roots
  id: local-docs
  relative_path: "official/example"
```

## Base Technology Packages

Base languages and web technologies are reusable knowledge packages and
capabilities, not platform contracts. A project platform contract may include
those packages directly or inherit them from a parent platform.

Knowledge package dependencies are manifest-driven. A package can declare
`dependencies` or `requires.knowledge_packages`, and doctors read those
dependencies generically for any package id.

## Application Or Domain Packages

Application and domain knowledge belongs in explicit packages chosen by the
workplace. A package should make its navigation contract clear:

- what local mirror, external documentation, API snapshot, or code snippet it
  points to;
- when the agent should load it;
- which package dependencies must be loaded first;
- whether a resource is required, recommended, or on demand.

If a package is planned but resources are not available yet, record a documented
placeholder status instead of a silent pass.

## Platform Composition Example

Example only: a documentation page may describe a real platform stack such as
Joomla -> JoomShopping. In that example the child package and child platform
depend on the parent package and parent platform. The same mechanics apply to
any workplace-defined parent/child platform stack; ProcessForge core does not
special-case those names.

## API Packages

API knowledge packages are named by provider:

```text
package id:   docs.api.<provider>
platform id:  platform.api-<provider>
registry id:  api-<provider>
```

Do not create one generic `docs.api` package for all providers. Each provider
gets its own package, platform, and registry id, for example
`docs.api.example-provider`, `platform.api-example-provider`, and
`api-example-provider`.
