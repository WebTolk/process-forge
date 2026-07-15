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
