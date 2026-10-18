# T02 acceptance cases

| Area | Expected result | Evidence |
|---|---|---|
| A -> B | Old Work never acquires B; current revocation of A blocks reads | before.json, new binding regression |
| Two Works | Separate capsule/checksum/generation/provenance; no shared cached text | new binding regression |
| Integrity | Wrong selectors, capsule digest, process pin, unknown binding rejected | new binding regression |
| Material | Changed/deleted/fulltext unavailable detected; metadata body change allowed | material module checks and binding regression |
| Stage | Missing inherits, empty returns no grants, expansion is invalid | binding regression |
| Transport | Real CLI/MCP same result, sessionless allowed, supplied invalid/foreign session denied | developer-probe.json, binding/MCP regressions |
| Continuation/evidence | Existing context survives lifecycle; artifact carries resource generation/hash | binding/pinned-process regressions |
| Coverage | Fresh physical index may have zero selected coverage; explicit scopes | shared-index/coverage tests |
| Bounds | No traversal/symlink read; raw and generated text/doc budgets explicit | material/binding regression |
| Compatibility | Project resource narrowing, policy, shared index, Work capsule and MCP cases | assurance-results.json |
| Public source | New schema, internal-ref equivalence, docs links/whitespace, clean public text and checksums | final checks |
