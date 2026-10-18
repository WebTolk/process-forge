# Handoff: local update metadata correction -> stable candidate parent

Objective: align local update index with release VERSION1.2.0.
Current status: data-only source slice accepted, native targeted/schema/cleanliness/checksum/release gates and primary review PASS; native closeout/doctors and publication receipts recorded separately.
Input artifacts: .pf/artifacts/pf120-local-update-index-20261018/report.md, targeted-checks.json, review.md, closeout.json, publication.json.
Exact run: garage-pf120-local-update-index-correction-20261018-fix-the-reproduced-r
Exact assignment: pf120-local-update-index-correction-20261018-fix-the-reproduced-release
Exact context: pf120-local-update-index-correction-20261018-fix-the-reproduced-release-capsule
Capsule checksum: sha256:f4f3bbbfb4497e0147557c521db726759bdfa791dd6ec59d41890996be4d92f5
Files changed: updates/processforge-update-index.yaml, checksums/processforge.sha256; own evidence/handoff only otherwise.
Files not to touch: immutable capsules, prior historical version rows, unrelated dirty/index state, active online stable feed, installed Core/Runtime/MCP.
Known issues: parent c4d6649/4bcd2250 candidate is superseded baseline; its incomplete consumer result is not a PASS.
Required checks: parent exact corrected-commit clean build and complete source/stress/consumer profile, new archive/hash/metadata, review/doctors/evidence delivery.
Next recommended action: read this exact correction commit from publication receipt, then continue existing parent Work; do not resume terminal correction or create duplicate release preparation.
