# Alpha3 publication metadata boundary

After the qualified alpha3 source/archive and both provider prereleases are
verified, update only the explicit alpha feed and retain the exact published
sidecar under release/1.3.0-alpha3/. Preserve historical alpha entries. The stable
feed is read only and its before/after SHA256 must match. The parent owns checksum
inventory updates; this disjoint primary delivery contribution does not edit it.

Do not invent archive URLs, hashes, size, source commit or release time. Read them
from the actual package/publication receipts. Validate the feed with the existing
update manifest validator and version-selection policy: alpha2 discovers alpha3
with the qualified artifact hash; stable selection excludes it. Read back public
feed/asset facts after both dev pushes. No device install, channel configuration,
Runtime/MCP action or stable publication is authorized by this contribution.

Primary performs this delivery step inside the same user result, without another
delegated executor. Implementation waits for actual successful publication.
