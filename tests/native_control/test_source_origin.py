"""Source entry spelling must preserve the captured file and code identity."""

from __future__ import annotations

import os
import sys
import types
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch


class SourceOriginTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[2]
        leaf = self.root / "tools/pf_native_control.py"
        self.source = leaf.read_bytes()
        self.native: Any = types.ModuleType("pf_native_control")
        self.native.__file__ = str(leaf)
        setattr(self.native, "_captured_source", self.source)
        self.module_patch = patch.dict(sys.modules, {"pf_native_control": self.native})
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)
        exec(
            compile(self.source, str(leaf), "exec", dont_inherit=True),
            vars(self.native),
        )
        self.entry = self.root / "tools/codex_exec_worker.py"
        self.entry_bytes = b"marker = 'captured entry'\n"
        self.publication = types.SimpleNamespace(
            payload={"tools/codex_exec_worker.py": self.entry_bytes}
        )

    def check(
        self, filename: str, *, code: bytes | None = None, file_value: str | None = None
    ) -> None:
        caller = types.SimpleNamespace(
            f_globals={"__file__": filename if file_value is None else file_value},
            f_code=compile(
                self.entry_bytes if code is None else code,
                filename,
                "exec",
                dont_inherit=True,
            ),
        )
        self.native._snapshot_origin(self.root, self.source, self.publication, caller)

    def test_supported_spellings(self) -> None:
        for filename in (
            str(self.entry),
            self.entry.as_posix(),
            str(self.entry.parent) + os.sep + "." + os.sep + self.entry.name,
        ):
            with self.subTest(filename=filename):
                self.check(filename)

    def test_different_file_or_code_is_refused(self) -> None:
        for filename, code, file_value in (
            (str(self.entry.with_name("other.py")), None, None),
            (str(self.entry), None, str(self.entry.with_name("other.py"))),
            (str(self.entry), b"marker = 'changed entry'\n", None),
        ):
            with (
                self.subTest(filename=filename),
                self.assertRaises(self.native.NativeControlError),
            ):
                self.check(filename, code=code, file_value=file_value)


if __name__ == "__main__":
    unittest.main()
