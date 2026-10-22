# Receipt evolution

2026-10-22. A useful live check must validate actual native receipts through the real running service, not just stored effects. My initial classifier guessed a captured status and the earlier source tests missed that conversation-only capture retains raw_accepted/duplicate_raw. Real-ingress first/replay regression cases now cover both actual values and both transport classifiers while preserving fail-closed denial behavior.

The original live message was not lost. Keep failed evidence and distinguish product defects from temporary verification mistakes: server status is a monitor projection, runtime status is service state, and persisted events use data while native envelopes use payload. Correct verification by reading the existing receipt, without replaying mutation.

One authorized server maintenance restart was sufficient. Only the client receipt function changed afterward; explicit AST parity and the real new-client/old-server HTTP path justify preserving the running server. Native apply is once per distinct qualified archive and namespace; earlier apply is never blindly retried. No further implementation, infrastructure action or memory update follows these lessons. Handoff: close and let the user execute the real Kimi retest.
