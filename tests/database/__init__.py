"""A1/A2 acceptance tests for the cold SQL foundation."""

from pathlib import Path
from uuid import uuid4

import pytest


@pytest.fixture
def isolated_path(request, tmp_path_factory):
    """Use declared evidence directories without pytest's restrictive mkdir mode.

    Windows managed execution cannot access pytest's mode-0700 temporary roots.
    Ordinary mkdir keeps inherited workspace permissions; no ACLs are changed.
    """
    base = request.config.getoption("basetemp")
    root = Path(base) if base else tmp_path_factory.getbasetemp()
    path = root / uuid4().hex
    path.mkdir(parents=True)
    return path
