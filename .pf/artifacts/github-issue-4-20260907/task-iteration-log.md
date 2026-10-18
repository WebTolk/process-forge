# Task Iteration Log: GitHub Issue #4

1. `analysis` — confirmed that the Core updater was archive-only while
   `workplace-init` generated unsafe `.candidate` proposals for an existing
   Workplace.
2. `implementation` — added archive-declared `copy_if_missing` and
   `append_registry_entry_if_missing` migration operations. The transaction
   backs up changed Workplace files under the Core update backup directory.
3. `test` — passed the focused Core-update smoke for plan, apply, user-value
   preservation, recovery classification after an injected write failure, and
   automatic post-update doctor execution.
4. `assurance` — passed Python compilation, schema validation, public
   cleanliness, checksum validation, and whitespace validation.

Release-test boundary: the public release test started and failed during its
clean-artifacts step because pre-existing `dist/` archives are stale. No archive
was deleted or repackaged by this task.
