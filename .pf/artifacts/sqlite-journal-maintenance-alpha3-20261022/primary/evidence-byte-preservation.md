# Exact evidence bytes in the final Git delivery

Independent R3 report bytes are already LF; its raw SHA256 and LF SHA256 are both
`f986aae9f5597122c7002408d15fe838b39c27cb4ebec2cbeaa1686c0a97bcd7`.
Some earlier primary JSON receipts contain CRLF. Keep those exact bytes and their
original evidence hashes; do not rewrite approved artifacts for text conversion.

The parent already owns `primary/**`. Its version-local `.gitattributes` disables
text conversion only inside this result's primary evidence directory. It permits
CR at EOL and original blank-at-EOF while retaining the other whitespace checks.
Native reports outside this directory that are already LF remain byte-identical
under the existing root attributes. Earlier CRLF worker summaries remain retained
locally; they are not rewritten or staged as normalized substitutes.

Unified patches retain the required single-space prefix on empty context lines;
sealed Markdown retains its two-space hard line breaks. Each Git whitespace
diagnostic for these formats is checked against the actual line before the
format-specific preservation exception. Other whitespace checks stay enabled.
No production source whitespace rule is relaxed by this evidence commit.

Final staging compares every selected Git blob directly with its actual artifact
bytes before commit. Native capsules, assignments/runtime records, full local
knowledge excerpts and raw private logs remain in the governed workspace; portable
receipts carry their exact identities, hashes and verification results. The actual
published sidecar has its separate version-local preservation rule in release/.
