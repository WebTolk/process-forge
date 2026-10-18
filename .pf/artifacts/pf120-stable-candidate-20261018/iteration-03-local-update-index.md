# Release finding: local update index still describes1.1.0

Reproduced on clean candidatec4d6649:

    version -> ProcessForge1.2.0
    self-update-check -> CURRENT1.1.0, LATEST1.1.0, UPDATE none

Cause: updates/processforge-update-index.yaml still has product.current_version1.1.0, stable.latest1.1.0 and no1.2.0 version record. The existing legacy self-update-check reads that local metadata directly. This is separate from the deliberately waived historical1.1.0 public asset mismatch and from the staged normalized online stable feed.

Required correction: narrow governed metadata-only contribution updating that local index for1.2.0 and its public checksum entry; retain prior version records and manifest_url. Verify default CURRENT/LATEST1.2.0 and an explicit previous1.1.0 sees available1.2.0 with migration guidance. No CLI/parser/runtime implementation change or public publication.

Current canonical4bcd2250 is now a baseline, not the final release candidate. Its complete source274PASS and stress6PASS remain truthful baseline evidence. Current native consumer run must not be relabeled as proof for changed bytes. Preserve its partial/raw evidence if stopped as superseded; rebuild from the correction commit and repeat the required complete source/stress/consumer profile before asking for publication approval.

Parent Work stays code-assurance with unchanged artifact-only capsule. Corrective source Work will have a separate non-overlapping product write scope and immutable context; parent will consume its exact committed result. No device install/restart or context refresh inferred.
