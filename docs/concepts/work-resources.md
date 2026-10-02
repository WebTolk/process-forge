# Work-scoped resource reads

The generated search documents also have a cumulative ceiling of 2,048 documents
and 32 MiB of UTF-8 content, including repeated metadata summaries.

Work-scoped reads let a caller search or resolve resources pinned to one
immutable governed Work. The CLI and MCP routes use the same source service.
They require the exact Run, Assignment and context id; they never select a
newer Work implicitly.

## CLI

Both commands require `--project-root`, `--run`, `--assignment` and
`--context-id`. `--workplace` may select the Workplace root explicitly and
`--json` prints the structured result.

```powershell
python tools/processforge.py work-search --project-root . --run RUN_ID --assignment ASSIGNMENT_ID --context-id CONTEXT_ID --query "deployment guide" --limit 10 --limitstart 0 --json
python tools/processforge.py work-resolve --project-root . --run RUN_ID --assignment ASSIGNMENT_ID --context-id CONTEXT_ID --resource-id RESOURCE_ID --json
```

Search accepts `--query` and the usual `--limit`, `--limitstart` and `--offset`
paging options. Resolve requires `--resource-id`. Add `--workplace PATH` to
either command when the Workplace cannot be selected by the project defaults.
For the exact context selector, use `context.id` from source `work-start` or
`work-state` output; `work.context_checksum` in a read response identifies the
capsule bytes that were checked.

## MCP

`pf.work.search` requires `run_id`, `assignment_id`, `context_id` and `query`;
it also accepts `limit`, `limitstart` and `offset`. `pf.work.resolve` requires
`run_id`, `assignment_id`, `context_id` and `resource_id`. Both retain the
existing project and bound-session authorization checks.

## What a read can return

A ready response is scoped to `work_context` and includes Work/context identity
and resource provenance, including the pinned generation and material
fingerprints. Search reports verified material coverage and returns matching
documents from the selected resources. Resolve distinguishes
`metadata_only` navigation from `verified_declared_material`; only the latter
has verified fulltext content. Blocked responses include a stable reason.
The feature reports source-level behavior; acceptance against an installed
Core and a real host remains pending.

Access is the intersection of the resources pinned to the Work, current project
authorization and the current process stage subset. An omitted stage subset
inherits the pinned grants; an empty subset grants nothing. Revoked access,
changed metadata or material, invalid scope, and missing or unverifiable
material block the read. A newly granted resource is not added to an older
Work. New governed capsules carry `resource_bindings.schema_version: 1`.
Existing context capsules are not rewritten: when their bindings are missing,
the read asks for a successor Work rather than silently migrating them.

For new Work bindings, resource materialization keeps grant membership from the
authorized local-search rows but treats the resolved resource declaration as the
authoritative indexing policy when it declares explicit `indexing` or recognized
legacy `index_policy` values. Legacy full-text spellings such as `fulltext` and
`full_text` materialize as fulltext; explicit `metadata` and `none` policies
remain non-fulltext and are not broadened by Work.

The process field `stage.resource_subset` narrows a Work's pinned resources.
Fulltext material is verified within fixed per-request budgets: at most 64
resources, 2,048 files, 32 MiB total content and 20,000 visited entries; each
resource is limited to 256 files and 8 MiB, and each file to 1,000,000 bytes.
Requests that exceed a limit are blocked rather than silently truncated.

Fulltext reads verify the declared, bounded material before searching it with
an ephemeral per-request FTS index. Content is not reused from a shared cache
or copied into a persistent corpus. Metadata-only resources bind their
declaration and source availability, not the changing contents of an output
tree. Returned provenance can be attached to artifact evidence; it records
what was read and does not grant future access.

An artifact evidence object can retain the returned provenance, for example:

```json
{
  "kind": "artifact",
  "artifact_id": "investigation-report",
  "status": "ready",
  "path": ".pf/artifacts/investigation-report.md",
  "resource_provenance": [
    {
      "project_id": "example",
      "run_id": "run-1",
      "assignment_id": "task-1",
      "context_id": "task-1-context-1",
      "context_checksum": "sha256:<capsule-digest>",
      "resource_id": "guide:root",
      "generation": "v1",
      "material_fingerprint": "sha256:<material-digest>"
    }
  ]
}
```

Common blocked reasons include `resource_access_revoked`,
`resource_material_changed`, `resource_generation_changed` and
`legacy_contract_incomplete`.

These routes complement project navigation (`pf.search` and `pf.resolve`),
which keep their existing project scope. Search-index readiness, current
authorized coverage and resource resolution are separate properties; a
ready project index does not prove that a Work's selected resources are
covered. See [the resource search index](resource-search-index.md) and
[the Work and execution contract](work-execution-contract.md).
