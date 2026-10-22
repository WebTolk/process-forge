# Primary review findings

2026-10-22. Primary self-review; no independent-agent claim. The immutable capsule
denies subagents despite the initial execution-mode intention; deny was respected.
Review compared actual normalizer/matcher and shared projection, canonical template,
declared options, byte/coverage identity, history and path boundaries.

Corrected during assurance:
- Explicit typing/narrowing in the small touched validator and new helper/tests;
  no acceptance rule change. Legacy nullable Path proof is made explicit.
- Invalid UTF-8 with BOM reports the decoder's actual offending line.
- Paired HTML tags are not bare template values; explicit literal declarations
  remain authoritative. Code-only required sections remain filled.
- Findings/link/file-byte limits are reported independently, including when finding
  output is truncated. Actual bounded stream read and external-target non-probing
  have focused tests. Empty angled Markdown destinations are explained.
- Generic N/A in evidence or a bare document and known supporting markers receive
  warnings; concrete explanation/support retains existing acceptance semantics.
- Repeated headings previously required repeated searches for section ends.
  A single stack pass now computes boundaries; inline delimiter masking also
  uses an explicit scan and heading/link regexes avoid overlapping unbounded
  suffix patterns. Adversarial repeated-heading, whitespace and delimiter cases
  supplement the byte limit. This does not extend the supported Markdown grammar.

No remaining issue found in primary review. This is not independent review or proof
of semantic truth. Final isolated QA results are reported separately. No historic
artifact normalization, new gate/blocker, facade/adapter/permissions change or
external fetch. Current/last-completed projection uses stored reports only.
