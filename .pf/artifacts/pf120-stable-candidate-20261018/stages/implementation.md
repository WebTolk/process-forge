# Implementation: candidate and promotion materials

Status: ready. 2026-10-18T04:01:05.417Z, primary/release-engineer.

Prepared clean detached LF sourcec4d66496464179750aa0448d11e4d2e797c2d2ff/tree3f7a2eff97f9391efd71d548bcc841103d9baf53. Product source/index unchanged; all writes are owned artifacts/scratch.

Native release-pack produced canonical processforge-1.2.0.zip, 2538276bytes,1309entries, SHA2564bcd22509ff15bd4c46febd078e3da596da0f0bf6a9eeb4104b2b75ce6aaaa12; separate sidecar37c7ff574819e56a673843052531c6838fc5a517ab3ec962fde3f5b1c2c22b62. Every source/payload/sidecar entry verified. Compared with accepted dev ZIP, only generated processforge-core.manifest.json differs; its1308-file inventory is identical. No private/derived entries.

Prepared proposed stable feed/historical sidecar, publication-metadata.patch and EN/RU release notes. Promotion patch changes exactly five paths: historical1.2.0sidecar, active-feed proposal, two existing QA expectations and their inventory. It remains unapplied to live source/channel. Native schema, checksum and four existing release metadata checks PASS; source binding uses the exact commit argument, not a claim that v1.2.0 already exists.

Actual published1.1.0 CLI in isolated fixture discovers1.2.0 with the exact proposed URL/hash and migration_required=true; apply without --confirm refuses before mutation. First fixture omitted required changelog_url and failed closed; field added, complete scenario rerun PASS, initial private log preserved. No device writes.

Scope respected. Complete source suite still running; supervisor-stress and complete extracted consumer remain mandatory. Handoff to assurance with ../plan.md, ../archive-identity.json, ../promotion-materials.json, ../previous-client-discovery.json and native check receipts; do not mark candidate qualified until all full gates finish.
