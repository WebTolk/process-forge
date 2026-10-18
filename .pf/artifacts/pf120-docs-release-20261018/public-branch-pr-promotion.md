# Pull requests for public default branches

The user's later instruction explicitly requires PRs and merging dev into main on
both providers. This supersedes the earlier direct-push promotion plan. Releases,
the immutable tag and their exact assets remain published and unchanged.

Create each PR with explicit dev/head and main/base, inspect the final content and
expected head before merging. Preserve main history, never force-push, and verify
the resulting tree equals the accepted delivery tree. GitHub uses gh; GitVerse uses
the token API and Git authentication helper. Read back actual merged PR state and
default-branch documentation. Reconcile provider merge ancestry by ordinary merge
or fast-forward if necessary; do not claim a closed PR is merged without readback.
