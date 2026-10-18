# Journal repair scope

Problem: full source schema validation fails on one invalid project journal record at line 34212. Goal: retain original evidence, quarantine only that invalid fragment without shifting/truncating an active append-only file, prevent concurrent new-version append/dedup races, and pass actual source validation.

Acceptance: original whole-file prefix backup and exact invalid bytes/hash retained; only its non-newline bytes replaced by equal-length whitespace (NDJSON readers explicitly skip blank lines); all original valid bytes and appended suffix preserved; separate ordinary repair-audit event records quarantine reference. Whole journal and full checkout schemas pass afterward. Real concurrent producer regression proves all complete unique records and one copy of duplicate id. Hook dispatch remains outside lock and behavior unchanged. Source/installed/connected-host rollout boundaries explicit.

No claim that the precise historical producer or the original full lost record is recovered. The malformed fragment has no event id. No rewrite of complete journal, deletion of history, reconstruction from guesses, validator weakening, new mandatory database, new public repair CLI or unrelated schema cleanup. This source fix will be included with the next standard updater delivery after the remaining T10 work; the already completed Core update is preserved.
