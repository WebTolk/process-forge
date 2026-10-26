# ProcessForge 1.3.0-beta1

This source candidate follows the internal alpha6 checkpoint and includes the
earlier alpha releases. It records stabilization of existing behavior; the
beta1 release-identity change adds no functionality.

Core identity continues to come from the owning distribution. Loaded identity
and live installed metadata remain separate, as do release, Runtime component,
protocol and schema versions. Existing CLI/MCP contracts remain in place.

The candidate includes fixes to owned worker scratch preparation, retry and
cancellation cleanup. Committed scratch bindings survive prepare retries, and
unpublished scratch is recovered before retry. Retention permission does not
replace ownership checks; required inputs, recovery data and durable evidence
remain protected. See [temporary files](../../docs/temporary-files.md).

Release verification preserves sealed reports, child failure output and
extracted evidence before disposal. `release-archive-test` again accepts an
omitted `--root`, using its existing default evidence root; an explicit root
retains source verification.

These notes do not establish beta acceptance or publication. Source checks,
archive qualification, installed Core checks and actual connected-host checks
are distinct evidence. Real OS cold-stop, restart and reboot operations require
a separate delivery operation. No beta update channel, tag, asset URL or package
hash is published by this metadata change; stable remains 1.2.0.

See [Core properties](../../docs/concepts/core-properties.md) for identity and
provenance limits. Final beta qualification and independent review remain open.
