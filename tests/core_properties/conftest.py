"""Isolated distributions for Core identity and adapter regressions."""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from processforge_core.common.properties import CoreProperties  # noqa: E402
from processforge_core.maintenance.update import (  # noqa: E402
    CORE_MANIFEST_NAME,
    make_core_manifest,
    manifest_bytes,
)


@pytest.fixture(
    params=["0.0.0", "7.12.3-alpha.4", "8.0.1-dev.23+local.7", "91.2.300+build.9"]
)
def release_label(request: pytest.FixtureRequest) -> str:
    """Exercise release labels independently of the tested checkout's version."""
    return str(request.param)


@pytest.fixture
def source_commit() -> str:
    """Return fixture provenance unrelated to repository HEAD."""
    return hashlib.sha256(b"core-properties fixture source").hexdigest()[:40]


@pytest.fixture
def write_distribution(source_commit: str) -> Callable[..., CoreProperties]:
    """Write native metadata and compose its real explicit reader."""

    def write(
        root: Path,
        version: str = "7.12.3-alpha.4",
        *,
        commit: str = source_commit,
        generated_at: str = "2024-01-02T03:04:05Z",
    ) -> CoreProperties:
        root.mkdir(parents=True, exist_ok=True)
        content = (version + "\n").encode("utf-8")
        (root / "VERSION").write_bytes(content)
        metadata = make_core_manifest(
            version=version,
            source={"vcs": "git", "commit": commit},
            files=[
                {
                    "relative_path": "VERSION",
                    "size": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            ],
            generated_at=generated_at,
        )
        (root / CORE_MANIFEST_NAME).write_bytes(manifest_bytes(metadata))
        return CoreProperties.from_distribution(root)

    return write
