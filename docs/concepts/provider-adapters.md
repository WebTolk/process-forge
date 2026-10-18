# Trusted Provider Adapters

ProcessForge separates raw event receipt from permission to create project effects. The raw-ingress kernel records a private receipt first. An accepted receipt is evidence that the input was durably received; it does not authorize a normalized event, ledger update, or conversation capture.

## Trusted registry

`tools/pf_runtime/provider_adapters.py` defines `AdapterPolicy`, `WorkerBinding`, and immutable `AdapterRegistry`. Application code constructs the registry from already-instantiated policy objects. Registry keys are the exact `(provider, adapter)` pair, duplicate or malformed keys are rejected, and `.policies` exposes the registered policies. Incoming event fields never import code, name a command, mutate the registry, or grant trust.

The source Host uses `DEFAULT_ADAPTER_REGISTRY` from `builtin_provider_adapters.py`. It contains the Codex hook adapter (`codex` / `codex-hooks`), the ProcessForge-owned Codex worker capture (`processforge` / `pf-codex-exec-worker`), and the normalized Runtime compatibility adapter (`processforge` / `runtime-legacy`). These names describe current source behavior; they do not establish installed-Core or connected-host qualification.

A trusted integration can construct a finite alternate registry in application code and pass it to `host.ingest_event`:

```python
from pf_runtime.provider_adapters import AdapterRegistry
from pf_runtime.builtin_provider_adapters import DEFAULT_ADAPTER_REGISTRY
from pf_runtime import host
from my_application.review_adapter import ReviewHooks

registry = AdapterRegistry([*DEFAULT_ADAPTER_REGISTRY.policies,
                            ReviewHooks("review", "review-hooks")])
result = host.ingest_event(envelope, workplace_root, core, registry=registry)
```

The example assumes a trusted application module implementing `ReviewHooks`. A policy must implement the pure `valid_raw_identity` check and `validate`; both default to refusal. `allows_message` also refuses by default. Validate provider identity controls, canonical derived fields and exact message provenance. The envelope must still pass Host's common project/session checks. The registered test adapter in `tools/smoke_provider_adapter_admission.py` demonstrates the complete integration boundary.

Invalid provider identity controls are persisted in a deterministic rejected-identity namespace with their raw payload unchanged. This prevents a forged stable/scope/version field from aliasing a legitimate receipt. Only after durable raw persistence does admission return denial. Codex replay compares the reconstructed canonical raw digest and recorded metadata before creating effects. A partial native envelope never falls back to normalized Runtime privileges.

## Admission and common checks

`host.ingest_event(..., registry=...)` first submits the native event to the raw kernel. If the receipt is accepted, Host resolves the exact registered policy and validates provider-specific provenance. An unknown pair is retained as raw-only with `adapter_untrusted`; a rejected or failing policy is raw-only with `provenance_rejected`. These stable diagnostics deny derived effects while preserving an accepted raw receipt. Kernel identity conflicts continue through the kernel's existing quarantine behavior.

Adapters interpret provider-specific event identities, content mappings, worker bindings, and message provenance. Host retains common project/session binding, current task and attempt authorization, output path and byte/hash checks, safe-content checks, durable writes, deterministic identities, deduplication, and deferred capture. Supplied derived identities must agree with the raw envelope. The event cannot select a more permissive policy or claim its own trust.

For worker capture, the adapter supplies neutral facts such as run, task, attempt, expected report, content, and hash. Host checks those facts against current assignment state and the declared report file. Codex hook interpretation remains in the Codex adapter; a recognized adapter may keep an unknown hook raw-only.

## Compatibility and initialization

The normalized Runtime compatibility adapter accepts only its already-normalized event on the authenticated Runtime path and rejects conversation messages. This preserves that transport's existing authentication boundary; it is not a general alternate-provider ingress route.

Generic project initialization and status treat Codex telemetry as optional. Missing or bounded failures in the optional status callback produce an unavailable informational read-model instead of blocking generic readiness. Hook installation remains an explicit `install_codex_hooks` repair action and requires the normal apply acknowledgement; initialization does not install hooks automatically.

These statements describe the source checkout. Installed Core, Workplace, and connected-host acceptance are separate T06 evidence and are not implied by source tests or documentation.

See the [Work execution contract](work-execution-contract.md), [Work context](work-context.md), and [session telemetry](session-telemetry.md).
