# Alpha3 code quality after independent review r1

Registered lint, formatting, strict mypy and Bandit all passed on the current
candidate; exact receipts are in qa-receipts-r2.json. Toolchain versions and narrow
legacy boundary exemptions remain those recorded in code-quality-report-r1.md.
No dependency or immutable contract/capsule was changed.

The raw replay check now uses the existing raw_payload_hash primitive and retains
receipt/record ID/hash and actual payload validation. It respects NFC identity
equivalence without losing stored-payload tamper detection. Scanner error/closure
paths verify and persist captured bytes plus source/line/offset/length/hash/reason
in a distinct immutable incomplete manifest. Completed earlier manifests remain
unchanged; conflict and source drift still raise. Failure evidence marks incomplete
preflight explicitly. EN/RU operator recovery guidance explains partial coverage.

The eight new regression cases and the whole source test suite pass. The primary
made these changes only after the first reviewer finished, under the same scoped
scanner/service/docs code-assurance Works. The before/after delta is retained in
review-r1-fixes.diff, and the previous NO-GO report is not rewritten. Independent
review of the new bytes and public release/archive gates remain pending.
