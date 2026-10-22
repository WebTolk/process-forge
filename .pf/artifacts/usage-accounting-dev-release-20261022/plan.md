# Dev release and device qualification plan

2026-10-22. User authorizes dev release, installation on this device and functional
verification; prior session authorization covers necessary PF App Server restart.
New bounded Work/capsule is valid, context ctx-20261021-162229-c46ea2 is fresh and
policy says continue. Earlier completed accounting Works are not resumed.

Source baseline is accepted dev head 8f918c3e89f33f06a976a05696c311a9e653a0a9.
Accounting source QA/review and two native usage/replay receipts passed. Main
checkout retains unrelated facade/platform refactor WIP. Build a clean detached
candidate under this Work's scratch, using only committed public source. Preserve
its LF byte form and regenerate shipped checksums there. Copy only the resulting
inventory back for a scoped metadata commit; build from that clean source commit.

Release identity remains 1.3.0-alpha1, with exact source SHA and archive hash
distinguishing this dev build. No stable tag/channel publication is requested.
Archive name is processforge-usage-accounting-dev-20261022.zip with its sidecar.
Check schemas, public cleanliness, checksums, release-check and relevant tests;
qualify extracted archive with the existing native archive-test. No executable
product change is planned, so prior same-byte Python lint/format/type evidence is
retained; repeat checks if product bytes need any authorized correction.

Install order: status, read-only plan, preservation fingerprints and workplace
database backup, one confirmed native Core apply, verify all managed installed
hashes, workplace doctor, status/repair and installed usage queries/replay. Core
and durable workplace data are distinct. Existing installation is 1.3.0-alpha1,
1462 managed files, incomplete_update=false. Never force over local modifications.

For functional proof, use installed CLI against the real project's shared store,
check exact captured counters and idempotent replay, then exercise installed driver
capture with a bounded safe subprocess. Distinguish real provider qualification
already obtained from the new installed-driver smoke. Inspect actual Runtime and
connected MCP provenance; restart only the intended PF App Server if necessary
and authorized. An independent stdio process alone is not actual host acceptance.

Knowledge READ_ACK: PF-resolved Python/practices/packaging resources; read PEP20,
packaging index, Core placement/OOP boundaries, project Python QA context and shared
Python toolchain contract. Existing release/update docs are operational authority.
No global legacy skill or dependency installation used. Initial dist/** scope was
rejected for overlap with a historical archive task; narrowed to two exact files
before Work creation. Old scope and capsule were not broadened.

Log substantive actions and hashes in this artifact directory. Finish native
lifecycle, scoped commit/push to both dev remotes (GitVerse through token), verify
both full SHAs, and stop after this release/install cycle.
