# Agent Search Query Analysis

Status: ready_for_review

`pf.context` now exposes a compact resource-selection summary: mode, target
versions, available and selected counts, and preferred resource identities.
Agents use that summary to understand scope before querying.

`pf.search` returns `document_id`, `resource_id`, relative locator,
provenance, and `match_reason`. `content` identifies a full-text hit;
`metadata` identifies a navigation hit. Agents must use `pf.resolve` for any
private local navigation and cannot infer roots from the available catalog.
