"""Reuse the private audit algorithm, keeping the original audit evidence immutable."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
source = ROOT / ".pf/artifacts/docs-audit-1.1.1-evidence/audit_inventory.py"
spec = importlib.util.spec_from_file_location("docs_inventory_algorithm", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.__file__ = __file__
module.main()
