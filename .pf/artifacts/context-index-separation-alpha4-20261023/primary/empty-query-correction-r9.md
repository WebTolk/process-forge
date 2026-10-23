# Empty maintained index query projection correction

The corrected user-like smoke retains the original empty-corpus assertion but
still fails after successful explicit maintenance. Actual investigation confirms
the common owner builds a valid zero-resource workplace index. Observation with
the catalogue snapshot reports fresh, but local_search.search rechecks unscoped
index_status(None), whose aggregate treats zero resources as missing. Access then
correctly propagates that nonfresh query result and exposes the inconsistency.

This is a production boundary defect, not an assertion to weaken. Keep the
original user-like empty/resource/Work predicates. Within the still-valid primary
review-fixes Work, update local_search.py and its owned regression file only.
An existing empty database is fresh only with an explicit valid fresh workplace
state proving zero resources/documents/allowed IDs and zero physical documents.
Absent DB, schema-only storage, stale/inconsistent state remain nonfresh. No
reader creates or maintains anything; no schema, fields or backend changes.

Cover initially empty manual maintenance and reconciliation after removal of all
resources, plus rejection of unmaintained/inconsistent empty state. Retain red
evidence. This supersedes r8's assumption that all production bytes would remain
unchanged. Freeze a new candidate, repeat whole pytest/static/affected native and
four corrected smoke checks, and get fresh independent review of this production
delta plus the fixture changes. All earlier candidates/GO reports and rejected
release attempts remain immutable. A new normal commit/push and both complete
unfiltered release profiles remain mandatory before publication.
