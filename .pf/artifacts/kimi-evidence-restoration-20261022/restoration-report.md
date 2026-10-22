# Restoration of Kimi's historical Git collateral

Restores 70 pre-existing PF evidence, assignment, run, handoff and log blobs changed only by newline normalization in `265767d9`. Every restored blob equals its original `6eeb4bac` preimage and current live bytes. Live files and checksum pins are unchanged. The primary Kimi remediation separately restores seven capsule blobs, for 77 original blobs in total.

Acceptance checks: exact parent/index/live equality for all 70; zero semantic diff after line-ending normalization; unrelated staged source/capsule corrections preserved. Two original trailing spaces in sealed run headings are retained as part of their original bytes, not autoformatted. Other restored paths pass Git whitespace checks.

No product behavior, dependency, installed component or infrastructure changed. Executable-code/browser/build gates are not applicable to this exact-byte evidence repair; checks are complete byte comparisons and index preservation, with private verification logs retained locally. Commit/provisioning readbacks belong to the combined qualified remediation delivery report.
