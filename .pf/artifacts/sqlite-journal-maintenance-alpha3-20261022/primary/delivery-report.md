# Alpha3 delivery: GO

Selected backlog: pf-maintenance-sqlite-journals-20261019. All seven criteria pass;
see [acceptance matrix](acceptance-matrix.md). Feature commit
`0bcf2a274a2097cf2ec84aa3a084644039390406`, bounded prerequisite/source commit
`18fd59e24d7b3ee7c79da26fb2b9001ee94469cd`. Both source dev remotes and the alpha3 tag were read back.

Published prerelease: [GitHub](https://github.com/WebTolk/process-forge/releases/tag/v1.3.0-alpha3), [GitVerse](https://gitverse.ru/webtolk/process-forge/releases/tag/v1.3.0-alpha3). Four published
assets were downloaded and hash/size verified after draft verification and again
after publication. ZIP SHA256 `b595a818827a286d6e4a9498991d1d4067935bea49e6c2018150bef9078a2022`, 2884284 bytes. GitVerse stores the
identical provenance sidecar with an additional .txt filename suffix.

Complete native committed-source public profile: 274 checks,
result PASS. Native ZIP/manifest/source freshness inspection, both extracted CLI
help entries, and complete retained extracted public profile:
272 checks, result PASS, without only/skip
filters. Extraction hashes match the published manifest before and after tests.

Actual alpha metadata commit `44882373a08fa42469bc141f6a06c0b411d92687` is confirmed in both dev refs;
the public alpha feed selects alpha3. Existing alpha1 objects and exact stable feed
bytes remain preserved; GitHub latest stable remains 1.2.0. The historical alpha3
sidecar equals the published sidecar. See [metadata delivery](metadata-delivery.json),
[readiness](release-readiness.json), source/archive receipts and native profiles.

QA: 530 pytest cases passed / 7 environment skips; ten existing evidence smoke
cases pass. Ruff lint/format, strict mypy and Bandit pass. Independent
[R3 CODE GO](../review/r3/report.md), with all prior reviews/failures retained.
Four native bounded contributions and one logical independent reviewer satisfy
the requested 1-1-4 composition. All foreign preservation guards passed.

Qualification is Windows CPython source and unpacked archive consumer usage.
Installed-device, connected-host and native POSIX acceptance remain separate.
No stable promotion, automatic data repair, continuation of paused OOP work or
additional product task is part of this delivery. Final lifecycle/accounting and
evidence commit follow; the primary then stops at the user-authorized boundary.
