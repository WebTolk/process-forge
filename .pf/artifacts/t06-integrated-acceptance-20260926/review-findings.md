# T06 semantic review

Reviewer: primary agent after implementation (single-agent process). Status: local changes reviewed; overall assurance remains incomplete pending updated installed-host acceptance.

Reviewed the new recovery smoke, its standard registration and bounded timeout, source prepared path/receipt behavior, existing worker fixture helpers, current Codex prompt/manifest/add-dir branches, changed EN/RU documentation, actual MCP response files, boundary-proof.json and final-checks.json.

Resolved findings:

- Real process-death/dead-owner lock and actual Junction refusal were only historical proof scripts. The new registered regression executes both. It requires exit 77 at the exact completion publication boundary, observes the durable receipt and missing completion, recovers in another process, then checks one event of each completion type and unchanged receipt bytes. The path test checks the concrete rejection code and no private bytes, then removes only the verified link.
- Governed worker collection needed persistent continuation coverage. The new fixture declares output/write scope before context creation, runs an offline generic executor, checks assignment/run/capsule bytes across two collections, reconnects through separate source MCP processes and advances only through valid stage evidence. The capsule stays unchanged after transition.
- Runtime driver docs described legacy mutable inputs and broad directory grants as universal. Corrected both languages and the worker example's report/scope declarations. Clarified that driver network/file declarations do not provide OS confinement. Added new Work read routes and exact-identity continuation guidance to MCP/lifecycle/Garage docs.

No remaining defect was found in these T06 source changes during this review. This is a semantic review, not an independent reviewer or proof of arbitrary executable isolation. The existing private T05 proof files and frozen earlier context are unchanged.

Unmet release-independent acceptance: installed/actual host still has T08 implementation. boundary-proof.json deterministically shows different MCP/Host hashes, missing installed work_context/diagnostics modules, and missing pf.work.search/pf.work.resolve. Both installations read the same T06 stage, but the source labels its installed-created immutable capsule legacy_contract_incomplete. It must not be rewritten. Updated-host feature acceptance requires a separately delivered build and new isolated fixture context; it cannot be waived by a source PASS or by refreshing the snapshot.

Source/installed stdio checks produced JSON-RPC-only stdout, silent notification handling, empty stderr and EOF exit 0. Actual application connection separately passed fresh context, unselected-resource denial and missing_session. No host-bound session was fabricated. Full current-source profile/privacy/Work-resource behavior on that actual connection remains unverified.

Harness correction: the initial assurance runner stopped before executing tests because it assumed an existing supplemental Runtime smoke was registered. The corrected harness explicitly labels that supplemental check; the failure is retained in assurance-preflight-failure.json. This was not a product failure and did not justify changing the product registry.
