# MCP Diagnostic Root Binding — 2026-10-16

The legacy optional diagnostic wrapper now compares the canonical session-bound
directory as well as project ID before choosing a project file sink. Another
directory with the same ID retains the existing null sink. This extends one
condition; the business dispatcher and its responses remain unchanged.

Eleven isolated controls use the real wrapper, dispatcher and JSONL sink, with
explicit fixture ports for session lookup and context freshness. Configured and
argument session forms previously wrote into a foreign same-ID directory; both
now create no diagnostic directory there. Bound and normalized paths, session-
only selection and supported project-only Garage logging retain correlated
records. Different IDs, conflicting or invalid sessions and missing roots retain
their outcomes. All eleven responses match the before-change responses. This
does not qualify live Ledger or an actual connected host.

Independent native PF review reproduced all 22 before/after rows and the old
wrapper's failing counterexample, with no blocking source finding. It also
reproduced a pre-existing limit: conflicting configured/requested sessions with
no `project_root` still write two records and a lock under the configured bound
root before returning `session_mismatch`, in both versions. This change does not
claim that every rejected request creates no files or enforce general business
project access. The review's optional build identity used its normal unavailable-
source fallback after an ungranted version-file body read was denied.

The existing MCP JSON-RPC, action-tool and missing-session checks pass. The
general diagnostics smoke fails its unchanged multiprocess-storage assertion;
the unmodified preceding check also fails there. Six separately observed native
child writers reproduced two Windows lock-acquisition `PermissionError` failures
in one writer, within the existing 50 ms wait budget. This qualification failure
remains open. No assertion or timeout was relaxed, and the MCP correction does
not change the diagnostic lock implementation.

Source, clean candidate/archive, installed Core, live Runtime and connected MCP
are separate evidence layers. The accumulated 1.2.0 candidate still requires full
qualification. Stable tags, public assets and channel updates require a detailed
readiness report and explicit user approval.
