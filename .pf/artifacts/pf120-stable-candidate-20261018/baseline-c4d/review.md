# Primary review: canonical1.2.0 candidate

Status: static review completed; full source/stress/consumer gates pending final consolidation. Independent agent not used: immutable capsule forbids subagents.

Implementation boundary verified: clean sourcec4d6649, fixed commit/tree/epoch and no live product/channel/device changes. ZIP/source/sidecar entries match; generated Core manifest is the sole delta against accepted dev, with identical1308-file inventory. Installed8ea152b evidence remains distinct; canonical candidate is not claimed as freshly installed metadata.

Promotion review: five exact follow-up paths, only two QA checksum entries changed, strict single-version/channel/prerelease/yanked/immutable-URL/hash/size checks retained. Seven malformed documents reject for expected reasons. Historical1.1.0 metadata preserved. Source binding on preview uses literal commit; real tag/source and HTTPS assets/feed must be read back during authorized publication. No TUF/signature capability invented.

Previous-client review: actual public1.1.0 archive and all933 sidecar entries verified; native dry-run discovery chooses1.2.0 with exact proposed URL/hash and migration_required=true. Both generic and Core apply refuse without confirmation before mutation; extracted Core and fixture bytes unchanged. File-provider proof does not replace live published HTTPS discovery.

Public promotion order matches maintainer contract: approve -> exact tag -> immutable assets/hash readback -> metadata commit/channel -> full remote/HTTPS discovery readback. Sidecar remains outside ZIP; metadata/source commit self-reference avoided. Raw patch storage preserves exact whitespace in gzip; readable final files separately available. Git may normalize historical sidecar text, so actual upload SHA remains separately recorded.

Known limits retained: intermediate OOP checkpoint, Windows/current Python qualification, optional fixtures/platform gaps, no new real provider-worker/device apply in this preparation, bounded shutdown history and partial metrics. Source full result must match entire native catalog before acceptance; consumer full remains mandatory on exact archive. No static finding requires changing the prepared payload.
