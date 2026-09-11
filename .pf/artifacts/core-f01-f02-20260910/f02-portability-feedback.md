# Primary review feedback for F02 attempt 1

The implementation's bounded preflight policy is reasonable, but current public smoke adds load_baseline_core_update()/assert_baseline_collision_reproduces() using git show HEAD. This is an actionable portability/lifecycle defect: release archives have no Git repository, and after committing this fix HEAD no longer has the old behavior. Do not collect/accept this attempt until corrected.

After terminal exit, retry the same worker scope with these requirements:

1. Remove all old-source Git loading and baseline-vulnerable-behavior assertions from tools/smoke_core_update_manifest.py, including unused types import. Public tests must work without .git or private .pf state and remain valid after this patch is committed.
2. Keep the real baseline reproduction as a separate private helper/raw evidence under your existing owned .pf/artifacts directory. Pin exact baseline revision from baseline.json or save source content into an isolated fixture; no shared-source reverting.
3. Strengthen collision no-mutation assertions: snapshot all pre-existing owned file bytes and manifest, plus user object bytes, and compare after each refused apply, including force. Directory content must be preserved, not just its type.
4. Run public smoke normally and from an isolated copy with only tracked public files plus any required new public files, explicitly excluding .git and .pf. Save output for both, using your own private scratch or system TemporaryDirectory.
5. Preserve first-attempt evidence. No broad changes or lifecycle operations.
