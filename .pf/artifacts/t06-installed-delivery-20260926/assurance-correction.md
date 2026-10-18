# Bounded documentation correction

2026-09-26: the extracted candidate passed 21/22 selected checks. smoke_docs_current_code_contract rejected the new T09 diagnostics usage placeholders, before installation. Preserve candidate-build.json and extracted-features.json as failed-candidate evidence; do not claim assurance-complete.

Scope refinement within delivery qualification: replace the three diagnostics CLI syntax lines in docs/concepts/diagnostics.md and docs/ru/concepts/diagnostics.md with executable parser-valid examples, explain optional filters in prose, refresh the owned checksum inventory, and make a successor isolated candidate. No runtime behavior change or edits to frozen evidence. Reuse 21 successful feature results only after proving every payload byte except these two docs and the checksum inventory is identical; rerun documentation, checksum and archive gates for the successor. This is a correction of an observed delivery blocker, not an unrelated feature.
