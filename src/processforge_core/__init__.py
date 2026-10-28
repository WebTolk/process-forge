"""Package bootstrap seam for direct-script ProcessForge runtime adapters."""

# This named package entry is part of the trusted entry boundary, like the
# direct-script entries. Capture before executing any Core business modules.
import sys as _sys
from pathlib import Path as _Path

_native_root = _Path(__file__).absolute().parents[2]
_native_path = _native_root / "tools/pf_native_control.py"
if _native_path.is_file():
    _native_module = _sys.modules.get("pf_native_control")
    if _native_module is None:
        _native_source = _native_path.read_bytes()
        _native_module = type(_sys)("pf_native_control")
        _native_module.__file__ = str(_native_path)
        setattr(_native_module, "_captured_source", _native_source)
        _sys.modules["pf_native_control"] = _native_module
        exec(
            compile(_native_source, str(_native_path), "exec", dont_inherit=True),
            _native_module.__dict__,
        )
    _captured_native_source = getattr(_native_module, "_captured_source", None)
    if isinstance(_captured_native_source, bytes):
        getattr(_native_module, "bootstrap_entry")(
            _native_root,
            trusted_leaf=_captured_native_source,
            _core_entry=_sys._getframe(),
        )
    elif getattr(_native_module, "_PUBLICATION_SEAL", None) is not None:
        raise getattr(_native_module, "NativeControlError")()

from .bootstrap import RuntimeBootstrap, bootstrap_runtime  # noqa: E402
from .composition import (  # noqa: E402
    build_configuration_provider,
    build_storage_migration_host,
)

__all__ = [
    "RuntimeBootstrap",
    "bootstrap_runtime",
    "build_configuration_provider",
    "build_storage_migration_host",
]
