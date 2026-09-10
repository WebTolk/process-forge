#!/usr/bin/env python3
"""Bounded smoke for raw-ingress checkpointed recovery.

The counters wrap the kernel's actual raw-record decoder, so the scaling
assertions measure historical JSON records and bytes rather than timings.
"""

from __future__ import annotations

import json
import multiprocessing
import tempfile
import argparse
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pf_runtime.raw_ingress_kernel as ingress
from pf_runtime.raw_ingress_kernel import NativeAgentEvent, RawIngressError, RawIngressKernel, atomic_write_json


FIXED_TIME = datetime(2026, 8, 15, 12, tzinfo=timezone.utc)


def event(number: int, *, stable: bool, session: str = "smoke") -> NativeAgentEvent:
    return NativeAgentEvent(
        provider="smoke",
        adapter="smoke-adapter",
        native_event_type="message",
        raw_payload={"number": number, "text": f"event-{number}"},
        native_event_id=f"native-{number}" if stable else None,
        native_id_scope="session",
        native_event_id_stable=stable,
        source_session_id=session,
    )


def append_without_indexes(kernel: RawIngressKernel, native: NativeAgentEvent) -> tuple[Path, int, dict[str, object]]:
    event_id = ingress.raw_event_id(native)
    payload_hash = ingress.raw_payload_hash(native.raw_payload)
    native_key = ingress.stable_native_identity_key(native)
    shard = kernel._shard(FIXED_TIME)
    line = ingress.canonical_json(kernel._raw_record(native, event_id, payload_hash, native_key, FIXED_TIME)) + b"\n"
    offset = kernel._append_line(shard, line)
    index = {
        "schema_version": 1,
        "raw_event_id": event_id,
        "raw_payload_hash": payload_hash,
        "native_identity_key": native_key,
        "raw_location": f"{shard.relative_to(kernel.root).as_posix()}:{offset}",
        "routing_status": "raw_accepted",
    }
    return shard, len(line), index


def with_decode_counter():
    counts = {"records": 0, "bytes": 0}
    original = RawIngressKernel._decode_raw_record

    def counted(self: RawIngressKernel, line: bytes, shard: Path):
        counts["records"] += 1
        counts["bytes"] += len(line)
        return original(self, line, shard)

    RawIngressKernel._decode_raw_record = counted
    return counts, original


def assert_incremental_scaling(root: Path, stable: bool, total: int) -> dict[str, object]:
    kernel = RawIngressKernel(root)
    kernel.ingest(event(0, stable=stable), FIXED_TIME)
    counts, original = with_decode_counter()
    try:
        for number in range(1, total + 1):
            receipt = RawIngressKernel(root).ingest(event(number, stable=stable), FIXED_TIME)
            assert receipt.accepted and not receipt.deduplicated, receipt
    finally:
        RawIngressKernel._decode_raw_record = original
    assert counts == {"records": 0, "bytes": 0}, (stable, total, counts)
    return {"stable_native_id": stable, "new_events": total, "historical_records_decoded": counts["records"], "historical_bytes_decoded": counts["bytes"]}


def assert_crash_recovery(root: Path) -> dict[str, object]:
    kernel = RawIngressKernel(root)
    seed = event(1, stable=True, session="crash")
    kernel.ingest(seed, FIXED_TIME)

    pending = event(2, stable=True, session="crash")
    shard, line_bytes, _index = append_without_indexes(kernel, pending)
    counts, original = with_decode_counter()
    try:
        receipt = RawIngressKernel(root).ingest(pending, FIXED_TIME)
    finally:
        RawIngressKernel._decode_raw_record = original
    assert receipt.accepted and receipt.deduplicated, receipt
    assert counts == {"records": 1, "bytes": line_bytes}, counts

    between = event(3, stable=True, session="crash")
    shard, line_bytes, index = append_without_indexes(kernel, between)
    raw_index = kernel._index_path("raw_event_id", ingress.raw_event_id(between))
    atomic_write_json(raw_index, index, kernel.root)
    counts, original = with_decode_counter()
    try:
        receipt = RawIngressKernel(root).ingest(between, FIXED_TIME)
    finally:
        RawIngressKernel._decode_raw_record = original
    assert receipt.accepted and receipt.deduplicated, receipt
    assert counts == {"records": 1, "bytes": line_bytes}, counts
    native_index = kernel._index_path("native_identity", ingress.stable_native_identity_key(between))
    assert native_index.is_file(), native_index

    partial = event(4, stable=True, session="crash")
    kernel.ingest(partial, FIXED_TIME)
    partial_index = kernel._index_path("raw_event_id", ingress.raw_event_id(partial))
    partial_index.write_bytes(b'{"schema_version": 1')
    counts, original = with_decode_counter()
    try:
        receipt = RawIngressKernel(root).ingest(partial, FIXED_TIME)
    finally:
        RawIngressKernel._decode_raw_record = original
    assert receipt.accepted and receipt.deduplicated, receipt
    assert counts["records"] >= 1 and counts["bytes"] >= 1, counts

    return {
        "append_before_index": {"historical_records_decoded": 1, "historical_bytes_decoded": line_bytes},
        "partial_index_write": {"historical_records_decoded": counts["records"], "historical_bytes_decoded": counts["bytes"]},
        "checkpoint": json.loads(kernel._recovery_checkpoint_path().read_text(encoding="utf-8")),
        "shard": shard.name,
    }


def assert_legacy_corruption(root: Path) -> dict[str, object]:
    legacy = event(10, stable=False, session="legacy")
    kernel = RawIngressKernel(root)
    _shard, legacy_bytes, _index = append_without_indexes(kernel, legacy)
    checkpoint = kernel._recovery_checkpoint_path()
    assert not checkpoint.exists()
    counts, original = with_decode_counter()
    try:
        receipt = RawIngressKernel(root).ingest(legacy, FIXED_TIME)
    finally:
        RawIngressKernel._decode_raw_record = original
    assert receipt.accepted and receipt.deduplicated, receipt
    assert counts == {"records": 1, "bytes": legacy_bytes}, counts
    assert checkpoint.is_file()

    corrupt = kernel._shard(FIXED_TIME)
    with corrupt.open("ab") as handle:
        handle.write(b'{"truncated":')
    try:
        RawIngressKernel(root).ingest(event(11, stable=False, session="legacy"), FIXED_TIME)
    except RawIngressError as exc:
        corruption = str(exc)
    else:
        raise AssertionError("truncated raw journal was accepted")
    return {"legacy_records_decoded": counts["records"], "legacy_bytes_decoded": counts["bytes"], "corruption_error": corruption}


def concurrent_submit(root: str, number: int) -> None:
    receipt = RawIngressKernel(root).ingest(event(number, stable=True, session="concurrent"), FIXED_TIME)
    if not receipt.accepted or receipt.deduplicated:
        raise AssertionError(receipt)


def assert_concurrency(root: Path) -> int:
    context = multiprocessing.get_context("spawn")
    processes = [context.Process(target=concurrent_submit, args=(str(root), number)) for number in range(20)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(30)
        assert process.exitcode == 0, process.exitcode
    shards = list((RawIngressKernel(root).root / "raw" / "v1").rglob("*.ndjson"))
    return sum(len(path.read_text(encoding="utf-8").splitlines()) for path in shards)


def assert_fault_boundaries(root: Path) -> None:
    for failure in ("raw_event_id", "native_identity", "checkpoint"):
        kernel = RawIngressKernel(root / failure)
        native = event(200, stable=True, session=failure)
        original = ingress.atomic_write_json

        def fail_index(path, data, boundary):
            if path.parent.name == failure or (failure == "checkpoint" and path.name == "recovery-checkpoint.json"):
                raise OSError("injected index/checkpoint failure")
            return original(path, data, boundary)

        with patch.object(ingress, "atomic_write_json", fail_index):
            try:
                kernel.ingest(native, FIXED_TIME)
            except OSError:
                pass
            else:
                raise AssertionError(f"fault was not injected: {failure}")
        shard = kernel._shard(FIXED_TIME)
        assert len(shard.read_bytes().splitlines()) == 1
        # The next request can be unrelated: recovery must index the pending
        # event before it commits a checkpoint for the newly accepted event.
        new = RawIngressKernel(root / failure).ingest(event(201, stable=False, session=failure), FIXED_TIME)
        assert new.accepted and not new.deduplicated
        duplicate = kernel.ingest(native, FIXED_TIME)
        assert duplicate.accepted and duplicate.deduplicated
        assert len(shard.read_bytes().splitlines()) == 2
        conflict = kernel.ingest(replace(native, raw_payload={"changed": True}), FIXED_TIME)
        assert not conflict.accepted and conflict.diagnostics["code"] == "native_id_payload_conflict"


def assert_shard_damage(root: Path) -> None:
    for damage in ("missing", "truncated", "all_missing", "invalid_object", "invalid_json", "missing_with_bad_index"):
        kernel = RawIngressKernel(root / damage)
        kernel.ingest(event(300, stable=True), FIXED_TIME)
        later = FIXED_TIME + timedelta(hours=1)
        kernel.ingest(event(301, stable=True), later)
        first, second = kernel._shard(FIXED_TIME), kernel._shard(later)
        if damage == "missing_with_bad_index":
            kernel._index_path("raw_event_id", ingress.raw_event_id(event(303, stable=False))).write_bytes(b"{")
            second.unlink()
        elif damage == "all_missing":
            first.unlink()
            second.unlink()
        elif damage in {"missing", "truncated"}:
            append_without_indexes(kernel, event(302, stable=True))
            if damage == "missing":
                second.unlink()
            else:
                second.write_bytes(b"")
        else:
            with first.open("ab") as handle:
                handle.write(b'{}\n' if damage == "invalid_object" else b'{broken json}\n')
        checkpoint = kernel._recovery_checkpoint_path().read_bytes()
        try:
            kernel.ingest(event(303, stable=False), FIXED_TIME)
        except RawIngressError:
            pass
        else:
            raise AssertionError(f"journal damage was hidden: {damage}")
        assert kernel._recovery_checkpoint_path().read_bytes() == checkpoint


def run(root: Path) -> int:
    results: dict[str, object] = {}
    results["stable_20"] = assert_incremental_scaling(root / "stable-20", True, 20)
    results["stable_100"] = assert_incremental_scaling(root / "stable-100", True, 100)
    results["sessionless_20"] = assert_incremental_scaling(root / "sessionless-20", False, 20)
    results["sessionless_100"] = assert_incremental_scaling(root / "sessionless-100", False, 100)
    results["crash_recovery"] = assert_crash_recovery(root / "crash")
    results["legacy_corruption"] = assert_legacy_corruption(root / "legacy")
    assert_fault_boundaries(root / "faults")
    results["fault_boundaries"] = "PASS: raw index, native index, checkpoint, unrelated next event, native conflict"
    assert_shard_damage(root / "damage")
    results["shard_damage"] = "PASS: missing, truncated, all missing, invalid identity, invalid JSON, missing with bad index"
    concurrency_root = root / "concurrency"
    results["concurrency_records"] = assert_concurrency(concurrency_root)
    assert results["concurrency_records"] == 20, results["concurrency_records"]
    print(json.dumps(results, indent=2, sort_keys=True))
    print("PASS: raw ingress incremental recovery smoke")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="writable scratch root; defaults to a temporary directory")
    args = parser.parse_args()
    if args.root is not None:
        args.root.mkdir(parents=True, exist_ok=True)
        return run(args.root)
    with tempfile.TemporaryDirectory(prefix="pf-f12-ingress-") as directory:
        return run(Path(directory))


if __name__ == "__main__":
    raise SystemExit(main())
