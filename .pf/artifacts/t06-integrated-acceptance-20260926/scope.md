# T06 scope and acceptance

Status: ready_for_review. Date: 2026-09-26. Authorization: current user resume plus r02 task cards and T05 handoff.

Goal: review and integrate the completed T02-T05/T08/T09 contracts; put real recovery/lifecycle/path-boundary regressions into the normal QA path; align broader EN/RU documentation with implemented API; capture actual connected MCP checks and source/installed limitations separately.

Allowed edits: affected smoke tests and release-test registration; docs/concepts/{context-capsule,garage-core,declarative-process-execution,runtime-drivers,runtime-mcp,prepared-input,work-context,work-resources,provider-adapters,diagnostics}.md and existing RU counterparts; checksums/processforge.sha256; this T06 artifacts/log/handoff and generated Work lifecycle. Necessary bounded fixes found by these tests must be documented before modification.

Forbidden: frozen earlier evidence, immutable capsules, unrelated dirty files, shared infrastructure, external projects, T07/T10/UI, public package/release or installation. Temporary tests belong below .pf/tmp or an isolated system temp directory.

Acceptance: deterministic regression of actual process death/dead-lock recovery, governed Work invariance and Windows Junction refusal; integrated Work/resource/context/provider/prepared-result tests; diagnostic profile invariance/redaction/retention/stdout checks; current actual MCP context/search/resolve/authorization and durable Work continuation; post-implementation semantic review; source QA and checksum/link cleanliness. Classify declaration, deterministic evidence and semantic review explicitly. Record source transport versus connected-host differences; never manufacture session identity. Host reconnect/session-bound/current-source delivery limitations remain explicit if unavailable in this session.

Migration risk: no API/schema migration is planned; added tests exercise existing contracts. Existing source changes stay uncommitted. Package/installed parity and full release qualification are outside local delivery and require an explicit later slice.
