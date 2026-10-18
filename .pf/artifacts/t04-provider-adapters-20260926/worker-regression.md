# T04 Provider Admission Regression

Role: regression writer. Scope: `tools/smoke_provider_adapter_admission.py` only; Host and RawIngressKernel were read-only.

The smoke uses a temporary generic project initialized by `smoke_conversation_completeness.setup_basic_project`, then calls `host.ingest_event` with a trusted fixture `AdapterPolicy` supplied in a caller-built `AdapterRegistry`. It passed these behavioral checks:

- A trusted alternate provider's session-start event routes; deleting its normalized effect and replaying the identical raw event repairs that effect exactly once.
- A trusted conversation message is recorded, and identical replay returns the same message identity without adding a second transcript row.
- Unknown provider and unknown adapter identities, session/source-project metadata mismatch, altered message content, and forged Codex derived `source.agent` or payload fields retain accepted raw receipts while producing no normalized or chat effects. The adapter/provenance reason is checked.
- A canonical Codex prompt was separately mutated at each raw identity control (`native_event_id`, `native_id_scope`, `native_event_id_stable`, and `payload_version`). Host admission retained each rejected raw receipt without normalized/chat effects. Calling `replay_session_raw_records` for that session denied all four forged records and created no message from their content.
- A partial native claim carrying a normalized `event_type` was retained raw and denied, with no fallback to legacy normalized routing.
- Reusing a stable native identity with changed raw payload is quarantined as `native_id_payload_conflict`.
- Duplicate adapter registration and non-policy registry entries are rejected.
- SHA-256 snapshots of `host.py` and `raw_ingress_kernel.py` match before and after the smoke.

Command: `python tools/smoke_provider_adapter_admission.py`

Result: exit code `0`; stdout: `PASS: trusted custom provider start/message, duplicate replay repair/idempotence, untrusted identity/provenance denial, forged Codex identity replay denial, partial-native raw-only denial, native-ID quarantine, duplicate registry rejection, Host/kernel/replay sources unchanged`.

Limits: this focused test does not repeat worker path/hash/session adversarial fixtures already owned by other smoke coverage, and does not exercise generic initialization with an unavailable optional Codex callback/module. No install, transition, or network operation was performed.
