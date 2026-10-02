# Investigation

## Findings

`command_release_archive_test` scaled the outer `run_release_command(..., timeout=max(1, int(1200 * timeout_scale)))` call, but did not append `--timeout-scale` to the nested extracted `release-test` argv. This meant the outer watchdog changed while the extracted release checks still used their default per-check budgets.

The existing timeout-scale parsing also used `float(getattr(args, "timeout_scale", 1.0) or 1.0)`. That made `0` behave like the default `1.0`, and non-finite values such as `nan` or `inf` were not rejected before later integer conversion or timeout use.

## Impact Analysis

Affected commands:

- `release-archive-test`: must pass the same finite positive scale to extracted `release-test` and use it for the outer extracted-test process timeout.
- `release-test`: must reject zero, negative and non-finite values before selecting/running checks.
- `dev-test` / `dogfood-test`: share the same timeout-scale contract and benefit from the common validator.

The change is local to CLI timeout handling and a focused smoke. It does not alter release command selection, archive inspection, packaging, manifest validation, Runtime/MCP, installed Core, or host behavior.

## Evidence

- `tools/processforge.py`: `positive_timeout_scale`, `command_release_test`, `command_dev_test`, `command_release_archive_test`, CLI help.
- `tools/smoke_release_archive_timeout_scale.py`: captures nested argv and outer timeout; covers default, positive, zero, negative, `nan`, and `inf`.
- `docs/known-limitations.md` and `docs/ru/known-limitations.md`: EN/RU contract note.
