# domain-modeling

Status: ready; primary / test-maintainer, 2026-10-17.

Internal constructor guard must represent deliberate dependency injection extension while preserving callers. Public CLI/MCP contracts and positional construction are unchanged. Name list remains exact, rather than weakening to subset. Explicit KEYWORD_ONLY and None checks prevent accidental required/positional dependency. Public release checksum uses LF Git bytes; only this file's inventory line can change.

Plan: ../plan.md. Follow the pinned process; do not mutate this evidence after transition.
