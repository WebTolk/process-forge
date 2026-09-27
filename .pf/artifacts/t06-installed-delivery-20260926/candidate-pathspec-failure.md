# Candidate staging harness correction

The first build attempt stopped before git add because passing all inventory paths in argv exceeded the Windows CreateProcess command-line limit (WinError 206). No commit, package or installation occurred. The candidate remained at the original detached HEAD with copied source bytes. Its pre-fix command/parity evidence is retained in candidate-build-before-pathspec-fix.json.

Use a NUL-delimited --pathspec-from-file for bounded exact staging. Resume verifies the same base HEAD and rechecks source/candidate product parity before staging. This is a packaging harness correction, not a product-code change or bypass of a quality gate.
