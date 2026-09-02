# Resource Selection Provenance Report

Status: ready_for_review

The snapshot now separates the complete available catalog from selected
resources. `resource_selection` records mode, target versions, available and
selected counts, and one provenance record per selector.

For the real Joomla-shaped context, the narrow legacy migration selected seven
resources from 27 available: direct documentation/toolkit/project resources and
the newest compatible 6.1 source tree. Historical v1 through v5 sources and
older 6.1 patches were not selected.

`pf.resolve` and `pf.search` consume only `knowledge_resources` and
`local_search_resources`; `available_knowledge_resources` is diagnostic data
and cannot authorize either operation.
