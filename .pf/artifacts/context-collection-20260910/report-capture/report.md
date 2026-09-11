# report-capture report

## Corrected diagnosis

The primary recheck reproduced the collector in isolated PF projects. Reports containing absolute or path-like text are rejected by automatic-content safety as `unsafe_automatic_content`. This is a content-policy failure, not a provenance failure.

Primary-run evidence:

- A normal report was collected successfully; the second collect was idempotent.
- A report containing an absolute Windows path was rejected with `unsafe_automatic_content` on both collection attempts.
- A report at the project-boundary expected-report path was collected successfully, confirming a separate containment case.
- Raw receipt deduplication still proceeds to conversation derivation. The earlier claim that duplicate raw ingestion returns early and permanently prevents recovery is incorrect.
- The earlier `untrusted_conversation_provenance` interpretation was also incorrect; the reproduced denial is `unsafe_automatic_content`.

Therefore, the completed reports rejected in the baseline are rejected because legitimate worker-report text contains path-like content, not because the worker failed to complete or because raw deduplication discarded the report.

## Minimal fix boundary

Adjust policy only for authorized `WorkerExpectedReportCaptured` output so legitimate path-like report text is permitted after all existing authorization, containment, raw-first, provenance, hash, secret-scanning, and exact-one-message checks pass.

Keep unchanged:

- expected-report containment and byte equality;
- task/run/attempt authorization;
- native event identity and raw-first ingestion;
- provenance validation;
- secret and malformed-content rejection;
- exactly-one assistant-message enforcement;
- idempotent collection behavior.

## Acceptance criteria

Add regression coverage proving:

1. First collection succeeds for reports with different valid contents and sizes.
2. Authorized reports containing Windows and POSIX path text are captured.
3. Repeating a successful collection is idempotent.
4. Raw receipt deduplication still permits required conversation derivation.
5. Wrong task/run/attempt/path, malformed identity or hash, secret-containing content, and untrusted provenance remain rejected.
6. Exactly-one-message enforcement remains intact.