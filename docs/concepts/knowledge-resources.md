# Knowledge Resources

Knowledge packages can either own their resources or reference external
resources through registries.

The MVP resource index records:

- resource id
- kind
- title
- path or `path_ref`
- load policy
- index policy
- short usage description

Heavy resources such as source trees and documentation mirrors should use
`load_policy: on_demand`. Smaller examples and snippets can use
`when_relevant`. Public project files must not contain private absolute paths;
private paths belong in workplace-local registries.

Supported MVP resource kinds:

- `source_tree`
- `documentation`
- `article_collection`
- `note_collection`
- `snippet_collection`
- `example_collection`
- `reference`
- `dataset`

Resource references can point relative to the package, relative to a knowledge
root, or through a workplace registry entry.
# Resource Indexes

Knowledge packages should publish `indexes/resource-index.yaml` for agent consumption. The index lists available resources, `path_ref`, `load_policy`, `index_policy`, source, license, and update policy.

Large resources such as source trees, full documentation mirrors, and article collections must default to `load_policy: on_demand`. Project snapshots select index records and do not load full resource content.

External and local private resources use `path_ref`; public snapshot records must not contain absolute local paths.
