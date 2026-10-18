# Pre-install release review correction

The first candidate was built but is NOT authorized as the final deliverable.
Before any Core apply, final extension review found that custom trusted tool
effects checked the local effect registry and immutable tool policy but did not
explicitly intersect Work action permissions. Shipped CLI only registers a pure
tool, yet the library extension boundary must honor the same deny dominance.

Corrected engine admission: a non-pure effect requires a Work allowed action;
any Work forbidden action wins, including pure effects. Synthetic privileged
credential fixture now explicitly grants the Work effect; separate ungranted
and locked-deny cases assert no tool execution. Policy bindings, current-stage
guard, capsule schema and native refusal are unchanged. Bilingual docs updated.

Correction stays within the accepted 30-file scope: engine, its focused test,
two egress docs and generated checksum inventory. Initial implementation,
assurance and first candidate observations remain intact. The first build's
final source preservation check must reject the superseded bytes; no update
apply has occurred. Final source reassessment and new candidate/archive/install
evidence live in `final/` under this same Work at release-delivery.

No other code or process scope changes. This is a pre-install assurance fix,
not a new parallel Work and not a claim that the first candidate was delivered.
