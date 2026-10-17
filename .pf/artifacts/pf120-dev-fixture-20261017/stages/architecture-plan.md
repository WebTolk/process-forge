# architecture-plan

Status: ready; primary / test-maintainer, 2026-10-17.

Minimal implementation: bind inspect.signature(...).parameters once, extend exact list by work_metadata, assert KEYWORD_ONLY and None default, leave all other test operations untouched. Compute SHA over canonical LF file and replace exactly one native inventory entry, assert no other entries changed. Run the existing seven-test smoke, syntax/diff checks and primary review; deliver test-only commit. Parent rebuilds a fresh candidate and qualifies full consumer suite, keeping first failed archive as superseded evidence.

Plan: ../plan.md. Follow the pinned process; do not mutate this evidence after transition.
