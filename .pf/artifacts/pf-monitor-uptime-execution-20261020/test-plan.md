# Test plan

Validate the authorized monitor display change on a separate candidate based on
accepted commit `7a4021788643e5df325f5ac1e1df1ab70ed02ac6`. Preserve the candidate's
sealed source hashes throughout all checks.

1. Demonstrate that focused regression cases fail before the change and pass
   after it. Test the actual module without launching host infrastructure.
2. Run the full `tests` collection through the registered PF Python QA launcher;
   explicitly read back any skip reason.
3. Run PF Python Ruff lint/format on the owning monitor module and new tests.
   Run mypy on the exact changed function bodies with real source imports;
   compare whole-owner diagnostics with the original source in the same import
   environment. Check the new function's docstring.
4. Run canonical `release-test --root . --public --fail-fast --timeout-scale 1
   --trace-smokes`, followed by `dev-test --root . --suite supervisor-stress
   --fail-fast --timeout-scale 1` on the isolated candidate.
5. Verify source hashes, distribution checksum rows, and source-only delivery
   scope. Reconcile native task/Work doctors and read back both remote heads.

The requested acceptance is source delivery. Final ZIP inspection, installation,
host reconnect, Runtime restart, and further task implementations are outside
this slice. Dependency audit is not needed because dependencies are unchanged.
