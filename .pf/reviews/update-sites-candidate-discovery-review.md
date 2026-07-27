# Review: Update Sites Candidate Discovery

## Result

pass_with_conditions

## Scope Reviewed

- Unified update-site schemas.
- Update CLI lifecycle commands.
- Deterministic local file-provider smokes.
- Project `.pf` assessment boundary.
- Tool update policy boundary.
- Public docs and release-test integration.

## Findings

No blocking findings in the implemented MVP slice.

## Conditions

- Do not claim `github_releases`, `gitlab_releases`, `gitverse_releases`, `generic_http_directory`, or `tuf_repository` as implemented until each has a deterministic smoke or a separately accepted waiver.
- Keep automatic source-checkout self-update apply out of default flows.
- Keep runtime update state outside public archives.

## Evidence

- New update smokes pass standalone.
- New update smokes pass through `release-test --only ... --public`.
- Full public release-test passes with and without `--fail-fast`.
- Release archive test passes.
- Clean extracted archive proof passes for the six update smokes and public fail-fast release-test; the only extracted warning is expected `git diff --check` skip outside a git repository.

## Residual Risk

Provider-specific remote release APIs remain deferred until each provider has smoke coverage.
