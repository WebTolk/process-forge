# Independent review r2: verify fixes and the full alpha3 candidate

This is the next clean review context for the same independent reviewer role.
The r1 report at ../review/r1/report.md remains CODE NO-GO with two mandatory P2
findings. Read it and review-r1-fix-plan.md, review-r1-fixes.diff and current
source-candidate-r3.json. For each manifest path, read candidate/path only; verify
all 26 hashes before and after review. No product writer runs concurrently.

Read test-report-r2.md, code-quality-report-r2.md, qa-receipts-r2.json and coverage
summary plus frozen architecture, actual Python excerpts/provenance, guidance and
current OOP rules. The full current QA passed: component145/6skip/65subtests,
whole523/7skip/143subtests, Ruff17fileformat/lint, strictmypy7, Bandit0findings.
Private raw command/log receipts are available in the declared project scratch.

Independently verify both corrections and remaining correctness of primary/W1-W4.
Use the actual native hash normalization for NFC payload equivalence and preserve
tamper detection; verify incomplete provenance on conflict, source drift and
generator closure and non-overwrite of a completed earlier manifest. Check the
application failure evidence and EN/RU recovery statements. Reassess all safety,
contract, cold composition and test concerns from review-input-r1.md. Optional
stdlib/in-memory probes are permitted; no Git, external tools/knowledge, PF
lifecycle, infrastructure, installs, other agents or product writes are permitted.

Emit actual READ_ACK after reading, then complete RESULT with CODE GO or NO-GO,
concrete canonical file/line findings and verification limits. Product fixes and
release acceptance belong to primary. Public committed-source/full archive and
consumer qualification are pending; do not claim device/connected-host alpha3.
Do not review your own product code; the primary implemented the corrections.
