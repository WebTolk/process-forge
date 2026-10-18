# Review follow-up design

Primary accepts the independently identified multi-root document collision as
a bounded search correctness repair in the same owned module. A document must
include its canonical authorized root in identity while preserving its public
relative path. Store a root digest in metadata and the private SQLite identity;
include it in freshness fingerprints and bump the derived schema. Preserve
overlapping-source deduplication within one root. Test two roots with the same
relative filename, two markers, and changes in either root.

Catch RuntimeError from symlink resolution alongside OSError for Python versions
which raise that form, without broad exception suppression. Current Windows
fixtures cannot create symlinks, so distinguish portable injected-resolution
coverage from real symlink coverage explicitly.

The migration concurrency note is an unverified pre-existing concern, not a
regression in A05. This run validates source preflight, apply-time archive fault
handling and durable partial backup evidence; simultaneous independent updater
applications are not asserted to be serialized.
