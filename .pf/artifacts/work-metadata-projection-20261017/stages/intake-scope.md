# Intake and scope

Brief: implement the common RAM metadata view designed in work-metadata-projection-design-20261017. Source baseline f3fecf7e4150a1b70c43a0cafcb2a0bfaba8392c. Product scope is the explicitly allowed work metadata/read/catalog/composition/MCP integration, relevant existing tests/docs/checksums, own scratch and evidence.

Acceptance: one explicit metadata pass reused by both pf.context consumers; compact content-keyed parse retention with unchanged limits; current reads each new operation; native selection/pending completion/summary policies and final full validation preserved; exact selectors avoid new inventory cost; relevant parity/freshness tests and cold/warm timing/parse/eviction/memory evidence; source committed and both dev remotes read back.

Excluded: new durable index/schema, new public operation, writer invalidation protocol, merging activity rules, pruning history, Runtime/MCP install/restart, changing already-requested device logging flags or releasing 1.2.0. Scope-accepted passed.
