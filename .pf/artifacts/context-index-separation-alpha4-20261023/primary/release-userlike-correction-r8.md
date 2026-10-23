# Remaining user-like Garage fixture correction

The remaining-check diagnostic on unchanged source commit 23ae1661 reproduced
smoke_user_like_garage_path expecting search.status=empty immediately after
onboarding. Actual context is fresh, search is explicitly stale, and governed Work
is created successfully. This is the same obsolete implicit-index assumption as
the three Garage search fixtures, not evidence of a production failure.

Use a separate disjoint Work for tools/smoke_user_like_garage_path.py only. Preserve
the original conditions, including empty corpus, resource scope and created Work.
Before explicit maintenance, assert context freshness, nonfresh empty search and
unchanged/absent fixture database; prove the existing Work start succeeds first.
Then invoke the canonical manual workplace maintenance CLI and rerun search for
the original empty-corpus assertions. Keep no-hooks/no-manual-infrastructure
semantics: indexing is an authorized file-only operation, never an infra restart.

Together with the three-file Work, validate four corrected native smokes, retain
all failed attempts and exact old guards, use registered Ruff, freeze a supplemental
candidate with byte-identical production/pytest files, and obtain supplemental
independent review before another normal commit/push. Repeat both complete
unfiltered source and exact archive release profiles. Diagnostic subsets do not
qualify a release. No production change, tag or publication is authorized yet.
