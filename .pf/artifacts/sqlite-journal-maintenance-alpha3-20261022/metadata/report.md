# Actual alpha3 publication metadata

The opt-in alpha feed and historical sidecar record the verified release of
source `18fd59e24d7b3ee7c79da26fb2b9001ee94469cd`, ZIP SHA256 `b595a818827a286d6e4a9498991d1d4067935bea49e6c2018150bef9078a2022` and size 2884284. All values come from
actual two-provider publication receipts. Sidecar bytes equal the published asset.
Metadata commit `44882373a08fa42469bc141f6a06c0b411d92687` is read back from both dev refs; the public
alpha feed was downloaded and confirmed at alpha3.

Native normalized manifest validation passed. Existing version policy selects
alpha3 from alpha1/alpha2, selects nothing newer from alpha3 or 1.3.0 stable, and
excludes alpha3 when filtering stable. Alpha1 objects and exact stable feed bytes
remain unchanged. Parent separately validated/refreshed checksums in a clean
delivery candidate, preserving foreign Main/resources/platform bytes.

This Work changes release data only; applicable assurance is actual published
asset comparison, native schema/version policy, exact Git blobs and remote refs.
Production Python quality is covered by parent R3 QA/review; no new Python owner
or extra deployment profile is introduced here. Its result is included in the
aggregate published alpha3 release and does not authorize a live device update.

Learning: publish immutable qualified bytes first, then bind actual distribution
hashes/URLs in a later metadata commit to avoid a circular archive self-hash.
No additional feature task remains in this bounded metadata contribution.
