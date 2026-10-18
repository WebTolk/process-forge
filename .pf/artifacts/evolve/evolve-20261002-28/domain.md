# Domain Modeling

## Domain Notes

Timeout handling in release validation has two layers:

- per-check budgets inside `release-test`;
- an outer process watchdog in `release-archive-test` while it runs extracted `release-test`.

The user-facing `--timeout-scale` value is a scale factor, not an absolute timeout. It must be accepted only when finite and greater than zero.

## Domain Model

- `timeout_scale`: finite positive floating-point multiplier.
- nested release test: extracted archive command `[python, tools/processforge.py, release-test, --root, <extract_root>, ...]`.
- outer watchdog: timeout used by `run_release_command("release-test extracted archive", ...)`.
- invalid values: zero, negative, `nan`, `inf`; all fail before command execution.

## Domain Rules

1. `release-archive-test --timeout-scale X` must append `--timeout-scale X` to the nested extracted `release-test` command.
2. The same scale may also multiply the outer extracted-test process timeout; this is a separate watchdog and does not replace per-check scaling.
3. Default/missing values use `1.0`; explicit `0` must not be treated as missing.
4. CLI help and documentation must not imply an absolute timeout or a hang fix.
5. Focused assurance must capture nested argv and the outer timeout rather than relying on a slower real release run.
