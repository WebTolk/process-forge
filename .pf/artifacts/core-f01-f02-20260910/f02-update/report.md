# F02 update report

## Result

Implemented bounded protection for archive-added Core paths:

- Added lexical collision checks covering files, directories, symlinks, dangling symlinks, and non-directory ancestors.
- Added stronger smoke assertions for no mutation, including forced applies and directory contents.
- Removed Git and `.pf` dependencies from the public smoke.
- Added private pinned-baseline reproduction evidence.

## Checks

- `py_compile` — exit 0.
- `git diff --check` — exit 0.
- Baseline reproduction at `1aecc18b6824204ca45ab30241b92d26e6d583a5` — baseline overwrote user data; repaired updater blocked with `plan_blocked`.
- Public smoke with private temp workaround — exit 0.
- Isolated public-only copy without `.git` or `.pf` — exit 0.
- Valid and dangling symlink cases explicitly skipped due Windows `WinError 1314` privileges.
- Normal `TemporaryDirectory` execution hit sandbox `WinError 5`; must be rerun outside this worker sandbox.

No docs, schemas, CLI, version, checksum, or lifecycle files were changed.