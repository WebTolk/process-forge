# F03/F04 primary acceptance
Status: accepted for sequential F05 implementation, not final batch closure.
Worker f0304-evidence durable exit 0 and collect DONE. Primary preserved the worker smoke and fixed harness problems: process configured before pinning; missing-digest file created; Forge-only can_complete replaced with direct service call in isolated fixture; added two distinct required evidence IDs.
Actual final new regression: f0304-final.json, exit 0, 199.245 seconds. Initial source and public-copy harness failures retained. Original baseline reproduction independently confirms all F03/F04/F05 failures; baseline public smoke fails on expected F03 stage_transitioned rather than incomplete.
Final portable acceptance will be rerun against complete F03-F05 source. No source core edits by primary in this slice; final worker already handled unsafe ValueError.
Ownership: primary transfers process_execution.py to f05-completion now; evidence smoke stays primary-owned and must be preserved by F05.
