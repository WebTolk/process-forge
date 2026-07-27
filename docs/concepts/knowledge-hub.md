# Knowledge Hub

The knowledge hub is a file-first internal workspace for reviewed learning
bundles and package releases:

```text
knowledge-hub/
  hub.yaml
  inbox/imports/
  candidates/index.yaml
  packages/docs.example/
  updates/
```

The MVP imports learning bundles, indexes candidates, builds package
`candidate-notes.md`, writes changelog/release plan files, creates a package
zip, and writes a local file-provider update manifest. Import preserves
`target`, `applicability`, `generalization`, `routing`, and `promotion`.

Package builds select candidates only when `routing.recommended_destination.id`
or `target.id` matches the package id. `source_context` is evidence, not a
destination. A candidate observed on a child platform is not included in a
parent package just because the parent platform appears in its source stack.

If a candidate targets a parent package but promotion is not approved, the hub
stages it in `resources/incoming-learnings.md` under `Unreviewed
parent-platform candidates`. It does not place that candidate in curated
`candidate-notes.md`.

The hub does not silently rewrite curated docs. Candidate notes are staged for
review, and released packages are distributed through the existing update
system.
