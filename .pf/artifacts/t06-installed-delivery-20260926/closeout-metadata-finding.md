# Closeout metadata finding (open)

Discovered after the normal MCP returned run_completed for delivery and continue_existing for original T06. This addendum does not replace or edit already registered delivery reports.

The final installed `run-doctor` reports one FAIL: delivery run.yaml contains a private absolute path. Its original objective, supplied to pf.work.start before delivery, includes the exact local Core installation path. The generated Run/Assignment/capsule copied that objective. `public_yaml_has_private_path` in tools/processforge.py checks serialized YAML for private absolute paths; completed-state/task/artifact consistency checks pass. This is an objective metadata defect, not an installed payload or Runtime failure. Raw evidence: closeout-doctor-first-observation.json and closeout-verification.json.

The capsule and pinned intent are immutable. Do not silently rewrite the original objective, regenerate its capsule, weaken the doctor, or claim a fully green delivery run-doctor. Existing delivery Work is recorded as completed by PF; operational installation/backup/config/tests remain verified. Original T06 is still incomplete pending real-host acceptance. This finding remains open for a separately governed metadata sanitization/export decision that preserves the historical intent and byte anchors.

Prevention for subsequent work: use portable target labels in objectives (installed Core test stand); keep machine paths in private delivery plans/evidence. No public publication occurred. Candidate public/archive validation passed and private governance files are outside the public distribution payload.
