# Release Tooling Worker Audit

Source: delegated read-only worker `audit-release-tooling-worker`.

Findings:

1. High: stale archive `dist/processforge-v1.0.0.zip` is still present and internally passes `release-archive-test`, while the current archive is `dist/processforge.zip`.
2. Medium: authoring parity WARNs are release-green; parity artifacts preserve WARN state but release-test still passes.
3. Low: `release-test` is not read-only. It runs `clean --release` first and can remove `.pf/runtime` generated state before validators inspect the tree.

Local verification:

- Confirmed both `dist/processforge-v1.0.0.zip` and `dist/processforge.zip` are present with different sizes and timestamps.
- Confirmed `release-test --root .` returns PASS.
- Confirmed release-test invokes `clean --release` before validation.
