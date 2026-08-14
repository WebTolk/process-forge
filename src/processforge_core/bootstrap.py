"""Bootstrap direct-script runtime adapters onto the packaged ProcessForge core."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

LEGACY_CORE_MODULE_NAME = "processforge_core._legacy_processforge"
LEGACY_PUBLIC_MODULE_NAME = "processforge"


@dataclass(frozen=True)
class RuntimeBootstrap:
    repo_root: Path
    core: ModuleType
    host: ModuleType
    service: ModuleType


def _repo_root_from(caller_file: str | Path) -> Path:
    caller_path = Path(caller_file).resolve()
    for candidate in (caller_path.parent, *caller_path.parents):
        if (candidate / "tools" / "processforge.py").is_file():
            return candidate
    raise RuntimeError(f"could not resolve repository root from {caller_path}")


def _ensure_sys_path(path: Path) -> None:
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)


def _cached_legacy_core(script_path: Path) -> ModuleType | None:
    for name in (LEGACY_CORE_MODULE_NAME, LEGACY_PUBLIC_MODULE_NAME):
        module = sys.modules.get(name)
        if isinstance(module, ModuleType) and Path(getattr(module, "__file__", "")).resolve() == script_path:
            sys.modules[LEGACY_CORE_MODULE_NAME] = module
            sys.modules[LEGACY_PUBLIC_MODULE_NAME] = module
            return module
    return None


def _load_legacy_core(repo_root: Path) -> ModuleType:
    script_path = (repo_root / "tools" / "processforge.py").resolve()
    cached = _cached_legacy_core(script_path)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(LEGACY_CORE_MODULE_NAME, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load legacy core module: {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[LEGACY_CORE_MODULE_NAME] = module
    sys.modules[LEGACY_PUBLIC_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        if sys.modules.get(LEGACY_CORE_MODULE_NAME) is module:
            sys.modules.pop(LEGACY_CORE_MODULE_NAME, None)
        if sys.modules.get(LEGACY_PUBLIC_MODULE_NAME) is module:
            sys.modules.pop(LEGACY_PUBLIC_MODULE_NAME, None)
        raise
    return module


def bootstrap_runtime(caller_file: str | Path) -> RuntimeBootstrap:
    repo_root = _repo_root_from(caller_file)
    _ensure_sys_path(repo_root / "src")
    _ensure_sys_path(repo_root / "tools")
    core = _load_legacy_core(repo_root)
    host = importlib.import_module("pf_runtime.host")
    service = importlib.import_module("pf_runtime.service")
    return RuntimeBootstrap(
        repo_root=repo_root,
        core=core,
        host=host,
        service=service,
    )
