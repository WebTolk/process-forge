"""Explicit trusted composition root. Never derive imports from event fields."""
from .provider_adapters import AdapterRegistry, RuntimeLegacyPolicy
from .codex_adapters import CodexHooksPolicy, CodexWorkerPolicy

DEFAULT_ADAPTER_REGISTRY = AdapterRegistry((
    RuntimeLegacyPolicy("processforge", "runtime-legacy", "none"),
    CodexHooksPolicy("codex", "codex-hooks"),
    CodexWorkerPolicy("processforge", "pf-codex-exec-worker", "worker"),
))
