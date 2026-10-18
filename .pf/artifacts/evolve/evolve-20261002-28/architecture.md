# Architecture Plan

## Architecture

Keep timeout-scale handling inside `tools/processforge.py` because the affected commands are CLI release helpers in that module. Introduce one local helper, `positive_timeout_scale(args)`, to keep the finite-positive contract consistent across `release-test`, `dev-test` / `dogfood-test`, and `release-archive-test`.

`release-archive-test` should continue to own the outer watchdog timeout for the extracted command, but it must also append `--timeout-scale <scale>` to the nested extracted `release-test` argv.

## Implementation Plan

1. Add finite-positive timeout-scale parsing.
2. Replace duplicated timeout-scale validation in release/dev/archive commands.
3. Append `--timeout-scale` to the extracted `release-test` command before launching it.
4. Add `tools/smoke_release_archive_timeout_scale.py` to capture nested argv and outer timeout, including default, positive, zero, negative and non-finite cases.
5. Update CLI help and EN/RU documentation.
6. Verify with focused smoke, compile, negative CLI checks, help, and diff whitespace checks.

## Decision Log

- Do not add separate CLI parameters for inner and outer timeouts in this fix; existing help describes one scale factor, and the acceptance asks for aligned parameter/documentation.
- Do not run full release archive qualification as proof of this change; the focused fixture captures the behavioral contract more directly and avoids treating longer runtime as a correctness signal.
- Share finite-positive validation with `dev-test` because it exposes the same `--timeout-scale` shape and had the same `0` / non-finite risk.
