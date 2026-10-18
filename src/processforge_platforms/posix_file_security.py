"""POSIX mode-preserving replacement; extended ACL support is not implied."""
from __future__ import annotations

import os
from pathlib import Path
import stat


class PosixFileSecurity:
    def descriptor(self, path: Path) -> None:
        return None

    def fingerprint(self, path: Path) -> str:
        return str(stat.S_IMODE(path.stat().st_mode))

    def restore(self, path: Path, descriptor: bytes) -> None:
        raise OSError("file_security_descriptor_unsupported")

    def replace(self, target: Path, staged: Path, mode: int) -> None:
        staged.chmod(mode)
        os.replace(staged, target)
