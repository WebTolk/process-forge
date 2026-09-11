# Context-origin report

## Finding

The stale result is caused by runtime/provenance divergence, not by the project snapshot itself.

Evidence:

- Source and installed commit are both `901d0551773fe7a5b382b89ebe95b212b0747e83`.
- The source snapshot and baseline snapshot contain identical `project_classification` data:
  - classifier: `processforge.official.software-web.classifier`
  - rule: `processforge.official.rule.python-marker`
  - source: `packs/official/software-development/project-classifiers/software-web.yaml`
- The connected MCP baseline reports `stale` solely because its recomputed classification differs from the snapshot: `project classification changed`.
- Current source `ProjectContextService.check()` correctly passes the resolved workplace to `project_context_check_result()`.
- MCP bootstrap loads the CLI and runtime relative to the MCP server’s own distribution root. Therefore a long-lived or differently rooted MCP process can resolve a different classifier catalogue/data provenance while reporting the same source commit.

The smallest meaningful difference is therefore the recomputed `project_classification` object, specifically classifier loading/path provenance. It is not an age, manifest, resource-generation, or project-file change.

## Reproduction

Run the same freshness check through both runtime roots against the unchanged project:

```powershell
python -c "import sys; sys.path.insert(0, 'tools'); import processforge; from pathlib import Path; p=Path('.').resolve(); w=processforge.resolve_workplace_manifest(p/'.pf/process-forge.local.yaml'); print(processforge.project_context_check_result(p, explicit_workplace=str(w) if w else None))"
```

Then invoke the connected MCP `pf.context` tool against the same project and workplace. Compare:

- `context.status`
- `context.stale_reasons`
- `project_classification.loaded_classifiers`
- `project_classification.matched_rules`
- each matched rule’s `source`

A correct implementation produces the same classification and freshness result in both paths.

## Root cause

The MCP path was not using the same effective runtime/data provenance as the source CLI at baseline. The MCP server’s bootstrap resolves its own distribution root and imports its own `tools/processforge.py`; classifier discovery then depends on that runtime’s workplace/catalogue inputs.

The source implementation already contains the necessary workplace propagation:

```python
ProjectContextService.check()
    -> project_context_check_result(
         project_root,
         explicit_workplace=str(self.workplace_root),
       )
```

Thus restarting or normalizing freshness output would only conceal the provenance mismatch. Legitimate classifier changes must continue to make the snapshot stale.

## Proposed minimal change

No public source change is justified from the supplied evidence. The minimal preventive change should be regression coverage that:

1. asserts MCP and CLI use the same resolved workplace;
2. records/compares the effective core module path and classifier paths;
3. compares the complete `project_classification` object before deciding freshness;
4. preserves `stale` when a classifier definition, registry entry, or resolved classifier source changes.

If the primary confirms an older installed `ProjectContextService`, the narrowly scoped fix is to pass `explicit_workplace=str(self.workplace_root)` exactly as the current source implementation does.

## Test design

- Same project/workplace through source CLI and MCP: identical classification and `fresh`.
- Same snapshot with a changed classifier rule: `stale`, reason `project classification changed`.
- Same snapshot with changed classifier registry/path provenance: `stale`.
- Different classifier catalogue with identical project files: `stale`; do not normalize classifier output.
- MCP launched from a separate distribution root: diagnostic must expose differing module/classifier provenance.
- Verify unrelated source/resource fingerprints remain unchanged.

No live refresh, installation, restart, or source modification was performed.