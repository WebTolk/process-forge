# Final corrected alpha4 code quality

Fresh registered Ruff lint/format passed 30 Python files and separately the four
actual changed Main functions with exact candidate AST equality. Strict mypy
passed 14 production modules; Bandit passed ten modules, 1596 LOC, zero findings
and no nosec/disabled-check skips. No production dependency was added.

Two bounded shared-layer corrections follow the r5 plan: required roots fail
collection on disappearance, including the source-stat race; optional missing
children and containment exclusions retain their meaning. Duplicate event replay
retries required invalidation using the already recorded event, without appending
duplicate audit rows. This is at-least-once notification delivery, not a new
transaction or delivery-receipt subsystem. All prior r4 guarantees remain as
documented. SQLite, the narrow backend Protocol and cold future scheduler remain;
no actual periodic registration, additional database or infrastructure change.
Fresh independent review and full release delivery remain required.
