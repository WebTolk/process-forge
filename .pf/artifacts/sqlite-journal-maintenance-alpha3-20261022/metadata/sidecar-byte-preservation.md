# Preserve the actual native publication sidecar

The qualified native alpha3 sidecar is 270480 bytes and contains 7482 CRLF pairs.
Its SHA256 is `f37c799e638319edec95464adcce5f3789f485d697dcf4eced367ff6ea2b9062`.
Archive/source inspection passed with these exact bytes; do not normalize them
or rewrite the immutable qualified artifact to accommodate Git text conversion.

The existing root attributes normalize text to LF. The metadata Work already
owns the entire new `release/1.3.0-alpha3/` directory. Add a version-local
`.gitattributes` with `*.manifest.json -text` there when recording the published
historical sidecar. This preserves its exact bytes in the Git blob and in future
checkouts. It affects only this new version's historical sidecar; existing alpha1
history and the root attributes stay unchanged.

Native schema validation and version selection still apply to the alpha feed.
Parent refreshes/validates the checksum inventory in its clean delivery candidate.
Before commit, compare the staged historical Git blob's SHA256 with the actual
published sidecar digest. This is a release-data preservation detail, with no new
production Python behavior or dependency.
