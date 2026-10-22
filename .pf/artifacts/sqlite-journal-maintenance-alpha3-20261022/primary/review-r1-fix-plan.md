# Mandatory corrections from independent review r1

Independent native reviewer r1 completed attempt2 with CODE NO-GO and two P2
findings. Preserve its report and all r1 source/QA manifests unchanged. No commit,
tag or publication is accepted yet. Native product writers and reviewer have
finished; primary performs the corrections under the existing exact scanner,
service and CLI-doc Work scopes at code-assurance, with one writer per scope.

1. Raw semantic replay must use the existing native payload hash primitive,
   including its NFC normalization, rather than a second JSON equality policy.
   Preserve receipt/record ID/hash checks and detect actual stored payload changes.
   Test composed/decomposed payloads, originals and repeat import without duplicates.
2. Scanner failure after capturing bad bytes must persist a verified incomplete
   provenance manifest and mark the supplied report incomplete. Keep identity
   conflict/source drift as errors. Use a separate immutable incomplete manifest
   name so a completed manifest from an earlier pass is never replaced. Test bad
   row followed by ID conflict, source drift and partial iterator closure.
   Application failure evidence must not claim quarantine was not requested when
   explicit capture was attempted; mark incomplete scan coverage truthfully.

Update EN/RU operator guidance, run meaningful regressions and all relevant QA,
freeze a new candidate manifest and request a new independent native review.
The public release/archive gates remain pending after code approval.
