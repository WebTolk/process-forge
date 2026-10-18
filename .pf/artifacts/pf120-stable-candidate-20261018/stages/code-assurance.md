# Code assurance: corrected canonical 1.2.0

Status: ready. 2026-10-18T05:41:28.448232+00:00; primary/release-engineer.

## Review findings

Primary review PASS in ../review.md. The reproduced local-index mismatch is closed by separately delivered source commit `f975d3a7f54100c310bf3dced0f0bbbc256a7738` and six exact source/archive coherence cases. No executable product changes were made in this parent Work. Earlier c4d source/stress success and intentionally incomplete consumer are retained as superseded baseline, excluded from current acceptance. Approved earlier stages remain immutable.

## Test plan

Native complete source --public/trace, required supervisor-stress, then complete extracted consumer, all with timeout-scale2 and no selective exclusions. Auxiliary metadata/predecessor-client/integrity cases are bound to the actual final archive. Full plan: ../test-plan.md. Native source catalogue/order is checked against all274 commands; public checks are separate.

## Test cases and report

| Case | Expected and observed | Evidence |
| --- | --- | --- |
| Complete source | 274PASS,3 public PASS; exact catalogue order | ../source-full-results.json |
| Required supervisor-stress | 6PASS in declared suite order | ../supervisor-stress-results.json |
| Exact archive consumer | Native full extracted release-test PASS, both CLI entry helps PASS | ../archive-consumer-results.json |
| Composition/provenance | All1309 ZIP entries and source/sidecar hashes match; only2 metadata payload changes plus generated Core provenance | ../archive-identity.json |
| Source/archive local version | Six native cases PASS: version/current/latest1.2.0, prior1.1.0 gets update and migration guide | ../local-version-coherence.json |
| Proposed publication | Six positive checks,7 expected malformed-feed rejections, patch apply/whitespace PASS | ../metadata-qualification.json |
| Previous1.1.0 client | Exact1.2.0 URL/SHA/migration; generic and Core apply refused without confirm; tree hashes unchanged | ../previous-client-discovery.json |

Source `f975d3a7f54100c310bf3dced0f0bbbc256a7738`, tree `4e0255cb70b9bfbe9007ed4b78908e841c070b95`. Archive `6b4d3b8b5996c3cd26002884823066e973ef508ecc340ea651deaff6594c19ca`; sidecar `f56162602030be36115a39283d71f5ac5dad1533b0659b69ee186b41901db8ac`. Current complete matrix: ../qualification-matrix.json. Source elapsed1627.870s; stress156.222s; consumer outer1499.685s.

Assurance complete for artifact preparation. Source/consumer/installed/Runtime/connected-host evidence remain distinct. No new installation or infrastructure lifecycle. Actual public tag/assets/stable channel and live previous-client HTTPS discovery require the separate explicit publication decision; they are not claimed here. Windows/current-Python/optional-fixture and intermediate-refactoring limits remain recorded. Browser verification is not applicable to this CLI/data-only package preparation.

Handoff: final report and reviewed publication bundle to release-delivery; native doctors and scoped dual-remote evidence delivery follow. Do not mutate the live channel or repeat device apply/restart.
