"""Native publication reads retain bounds without allocating the full limit."""

from __future__ import annotations

import os
import tracemalloc

import pf_native_control as native
import pytest

READERS = [native._read_regular]
if os.name == "posix":
    READERS.append(native._snapshot_read_regular)


@pytest.mark.parametrize("read", READERS)
def test_tiny_publication_read_does_not_allocate_the_file_limit(tmp_path, read):
    payload = b"1.3.0-beta3\n"
    (tmp_path / "VERSION").write_bytes(payload)
    tracemalloc.start()
    try:
        assert read(tmp_path, "VERSION", native.MAX_FILE) == payload
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 1024 * 1024, peak


@pytest.mark.parametrize("read", READERS)
@pytest.mark.parametrize("size", [0, 1, 65539])
def test_publication_read_preserves_exact_bytes_at_limit(tmp_path, read, size):
    payload = bytes(range(256)) * (size // 256) + bytes(range(size % 256))
    (tmp_path / "payload").write_bytes(payload)
    assert read(tmp_path, "payload", size) == payload


@pytest.mark.parametrize("read", READERS)
@pytest.mark.parametrize("limit", [0, 1, 65536])
def test_publication_read_refuses_one_byte_beyond_limit(tmp_path, read, limit):
    (tmp_path / "payload").write_bytes(b"x" * (limit + 1))
    with pytest.raises(native.Refusal, match="read_limit"):
        read(tmp_path, "payload", limit)
