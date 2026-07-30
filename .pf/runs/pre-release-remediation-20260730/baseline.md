# Remediation Baseline

- captured_at: 2026-07-30T06:40:30Z
- branch: `main`
- HEAD: `2e8941b995644dcdc259d3a1618a4fafbf2b42f4`
- origin/main: `2e8941b995644dcdc259d3a1618a4fafbf2b42f4`
- working_tree: dirty before remediation
- non-remediation status entries observed: 92
- prior completed slice: official bundled process packs

The existing product and release changes belong to the preceding completed
slice. Remediation changes must be reported separately and must not revert or
silently absorb unrelated work.

Assignment capsule generation was attempted for all three worker assignments.
The CLI refused because the project context snapshot reports three missing
required capabilities. Workers therefore receive the validated assignment YAML
directly, plus Agent Ledger identity and an explicit lease. No synthetic capsule
was created and the limitation must remain visible in final evidence.
