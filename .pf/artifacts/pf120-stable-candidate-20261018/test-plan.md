# Assurance plan and cases

Scope: exact source f975d3a7f54100c310bf3dced0f0bbbc256a7738 and canonical ZIP identified by archive-identity.json. Relative to accepted dev, the only payload changes are the local update index and its checksum; generated Core provenance also changes. Earlier c4d results are retained as baseline only. Existing actual-host acceptance remains separate from source/archive qualification.

Mandatory complete gates:

- Source: native release-test --public --trace-smokes --timeout-scale 2. No --only/--skip or fail-fast truncation. Compare structured report labels against the full native --list catalogue in exact order; retain all statuses and public checks.
- Required development suite: native dev-test --suite supervisor-stress --timeout-scale 2; retain complete result and any fixture/platform limitations.
- Consumer: native release-archive-test --extracted-test full --timeout-scale 2 on the exact ZIP and clean source. Native outer timeout is 2400 seconds. Execute full source, stress and consumer sequentially.
- Artifact integrity: source/sidecar/ZIP hashes and every entry, full comparison with accepted dev, exactly 1308 non-generated entries and 1309 total, no private/derived entries. Require exactly the two metadata payload changes and generated Core provenance.
- Local version coherence: clean source and safe extracted ZIP both report version 1.2.0 and self-update-check CURRENT/LATEST 1.2.0. Explicit prior version 1.1.0 reports available 1.2.0 and migration guidance. This targeted gate covers the relationship missed by the existing full catalogue.
- Proposed promotion: normalized manifest schema, inventory, four existing metadata smokes, seven malformed-feed rejection cases, patch apply-check and whitespace. Source binding uses the exact commit; an actual public tag is not yet created.
- Previous client: actual public 1.1.0 archive and all 933 sidecar entries verified; isolated native dry-run discovery selects exact proposed 1.2.0 URL/SHA with migration_required. Both generic and Core apply refuse without confirmation, with Core/fixture tree hashes unchanged.

Safe receipts remain here; raw logs, native structured source report/trace, canonical files and isolated fixtures remain in owned scratch. A successful native full consumer invocation is separate evidence; source results are never relabeled as consumer or installed acceptance. Record actual warnings and optional/platform limitations.

Final primary review follows implementation and successful gates. Native doctors and scoped commit/push/full-SHA readback to both dev remotes complete delivery. Public tag/assets/stable promotion and device operations remain outside this preparation.
