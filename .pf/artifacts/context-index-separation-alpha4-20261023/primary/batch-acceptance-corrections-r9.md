# Actual CLI and native acceptance corrections

The first actual-CLI fixture failed before batch execution: native authoring's
UpdateSchemaChecks rejects the already-declared local resource-indexing.schema.json
reference in package-manifest.schema.json. The fixture also omitted that schema's
required enabled flag. Fix the fixture, and enable exactly this bundled local
schema reference with its own internal-ref root. Keep every other external ref
rejected; no URL or arbitrary path resolution, no dependency, no weakened schema.
Add real-schema success/negative/unavailable-file/unknown-ref tests in a new
bounded primary contribution. A selected policy remains fully validated.

The newly added affected native context-readiness smoke retains a legacy fixture
assumption: project refresh clears global registration invalidation. Under the
frozen alpha4 contract it cannot. Keep all existing freshness, readiness, search,
authorization and MCP assertions; explicitly maintain the fixture workplace before
its positive search assertion. No product workaround or relaxed assertion.

URL-backed records normalized by native authoring use legacy full_text by default
but have no local document body. Project that legacy external-reference default
to metadata only; explicit structured fulltext policies still fail without a local
root rather than downloading or silently changing policy. The common backend
must use the same rule in partial and full passes. Add default/exclusion probes.

Native batch contribution has actually completed exit zero in attempt 2, with its
31 test scenarios handed to primary QA. The initial r11 candidate and all failing
receipts remain historical unreviewed evidence, no CODE GO. Required corrections
are sequential; a new frozen candidate/full QA/fresh independent review follow.
