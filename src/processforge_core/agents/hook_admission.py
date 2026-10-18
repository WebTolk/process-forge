"""Mode-aware automatic hook admission; no storage or infrastructure effects."""
from ..configuration.models import PFConfig


def collect_hooks(effective_mode: str, config: PFConfig) -> bool:
    if effective_mode not in {"simple", "organized"}:
        raise ValueError("hook_coordination_mode_invalid")
    return effective_mode == "organized" or config.runtime.garage_hooks
