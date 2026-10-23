"""Isolated distributions for Core identity and adapter regressions."""

from __future__ import annotations

import hashlib
import importlib
import sys
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from processforge_core import composition  # noqa: E402
from processforge_core.bootstrap import RuntimeBootstrap  # noqa: E402
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


@pytest.fixture
def adapters(tmp_path, monkeypatch, write_distribution):
    """Bind the actual adapters to one fixture owner without starting infrastructure."""
    root = tmp_path / "distribution"
    properties = write_distribution(root)
    factory = Mock(return_value=properties)
    monkeypatch.setattr(composition, "build_core_properties", factory)
    cli = importlib.import_module("processforge")
    monkeypatch.setattr(cli, "CORE_PROPERTIES", properties)
    from pf_runtime import host, mcp_server, monitor, service

    workplace = tmp_path / "workplace"
    workplace.mkdir()
    project = tmp_path / "project"
    (project / ".pf").mkdir(parents=True)
    (project / ".pf/process-forge.yaml").write_text(
        "project:\n  id: fixture\n", encoding="utf-8"
    )
    runtime = RuntimeBootstrap(root, cli, host, service)
    return SimpleNamespace(
        root=root,
        properties=properties,
        factory=factory,
        cli=cli,
        host=host,
        mcp=mcp_server,
        monitor=monitor,
        service=service,
        workplace=workplace,
        project=project,
        runtime=runtime,
    )
