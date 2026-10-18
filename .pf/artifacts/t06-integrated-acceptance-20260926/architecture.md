# T06 implementation plan and decisions

Status: ready_for_review. No production contract change.

1. Add tools/smoke_prepared_execution_recovery.py with isolated governed offline execution/collection/reconnect/stage-transition proof, actual abrupt collector exit and exactly-once recovery, and actual Junction/symlink private-file refusal. Declare governed fixture scope before capsule creation; never repair a generated capsule/hash to obtain a positive result. Use new source stdio connections to check persisted continuation, and label this proof accurately.
2. Register the new regression beside smoke_prepared_execution_context with a bounded timeout. Keep original T05 proof/evidence untouched.
3. Correct existing EN/RU runtime-drivers behavior/examples; explain Work versus project resource navigation, pinned continuation and collection in the broader concept docs. Preserve provider-specific behavior in adapter documentation.
4. Run focused new regression, then the existing integration/compatibility and diagnostic suites, source schema/public/checksum/link QA. Inspect changes semantically after implementation. No UI test applies.
5. Capture real connected MCP context/search/resolve, denial and Work continuation. Use separate installed stdio reconnect where possible, with no invented host sessions and no infrastructure restart. Record missing new-source host capabilities as an unmet acceptance boundary.

Rollback: revert only T06 additions and its bounded doc/registration hunks; existing dirty source and frozen earlier artifacts are preserved. No package migration or installed rollback is required because no installation occurs. Do not mark the whole T06 assurance gate passed if required updated-host acceptance is absent.
