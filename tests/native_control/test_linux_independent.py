"""Mapping refusals and real independent ephemeral namespace qualification."""

from __future__ import annotations

import errno
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pf_linux_native_control as linux
import pf_native_control as native
import pytest


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "NSpid: 0",
        "NSpid: -1",
        "NSpid: １",
        "NSpid: 2147483648",
        "NSpid: 3\nNSpid: 3",
        "NSpid: 3 nope",
    ],
)
def test_mapping_rejects_missing_hidden_or_malformed_vectors(raw: str) -> None:
    with pytest.raises(linux.LinuxControlError, match="linux_pid_mapping_invalid"):
        linux._pid_numbers(raw, "NSpid")


def test_mapping_accepts_ancestor_procfs_vector() -> None:
    assert linux._pid_numbers("Name: python\nNSpid:\t710\t9\t2\n", "NSpid") == (
        710,
        9,
        2,
    )


@pytest.mark.parametrize(
    ("mapped", "ticks", "ready", "expected"),
    [
        ((710, 9), "33", False, None),
        ((711, 9), "33", False, "linux_pidfd_mapping_mismatch"),
        ((710, 10), "33", False, "linux_pidfd_mapping_mismatch"),
        ((710,), "33", False, "linux_pidfd_mapping_mismatch"),
        ((710, 9), "34", False, "linux_process_birth_mismatch"),
        ((710, 9), "33", True, "linux_process_observation_unavailable"),
    ],
)
def test_retained_mapping_rejects_sibling_reuse_or_exit(
    monkeypatch: pytest.MonkeyPatch,
    mapped: tuple[int, ...],
    ticks: str,
    ready: bool,
    expected: str | None,
) -> None:
    closed: list[int] = []
    monkeypatch.setattr(
        linux, "os", SimpleNamespace(pidfd_open=lambda pid: 42, close=closed.append)
    )
    monkeypatch.setattr(linux, "_self_pids", lambda: (700, 8))
    monkeypatch.setattr(linux, "_pidfd_pids", lambda fd: mapped)
    monkeypatch.setattr(linux, "_ticks", lambda pid: ticks)
    monkeypatch.setattr(linux, "_ready", lambda fd: ready)
    if expected is None:
        assert linux._retain_ephemeral(9, 710, "33") == 42
        assert closed == []
    else:
        with pytest.raises(linux.LinuxControlError, match=expected):
            linux._retain_ephemeral(9, 710, "33")
        assert closed == [42]


@pytest.mark.parametrize("number", [errno.EACCES, errno.EIO])
def test_mapping_preserves_observation_error_and_releases_handle(
    monkeypatch: pytest.MonkeyPatch, number: int
) -> None:
    closed: list[int] = []
    error = OSError(number, "fixture observation denied")
    monkeypatch.setattr(
        linux, "os", SimpleNamespace(pidfd_open=lambda pid: 42, close=closed.append)
    )
    monkeypatch.setattr(linux, "_self_pids", lambda: (700, 8))

    def refuse(fd: int) -> tuple[int, ...]:
        raise error

    monkeypatch.setattr(linux, "_pidfd_pids", refuse)
    with pytest.raises(OSError) as caught:
        linux._retain_ephemeral(9, 710, "33")
    assert caught.value is error
    assert closed == [42]


def test_mapping_rechecks_handle_after_birth_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed: list[int] = []
    mappings = iter([(710, 9), (711, 9)])
    monkeypatch.setattr(
        linux, "os", SimpleNamespace(pidfd_open=lambda pid: 42, close=closed.append)
    )
    monkeypatch.setattr(linux, "_self_pids", lambda: (700, 8))
    monkeypatch.setattr(linux, "_pidfd_pids", lambda fd: next(mappings))
    monkeypatch.setattr(linux, "_ticks", lambda pid: "33")
    with pytest.raises(
        linux.LinuxControlError, match="linux_process_observation_unavailable"
    ):
        linux._retain_ephemeral(9, 710, "33")
    assert closed == [42]


def test_ephemeral_close_attempts_both_descriptors_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed: list[int] = []
    failure = OSError(errno.EIO, "fixture close failure")

    def close(fd: int) -> None:
        closed.append(fd)
        if fd == 42:
            raise failure

    job = object.__new__(linux.EphemeralNamespace)
    job.carrier, job.init, job.closed = 42, 43, False
    monkeypatch.setattr(linux, "os", SimpleNamespace(close=close))
    with pytest.raises(OSError) as caught:
        job.close()
    assert caught.value is failure
    assert closed == [42, 43] and job.closed
    assert job.carrier is None and job.init is None
    job.close()


@pytest.mark.parametrize(
    "raw",
    [
        "Pid: 710\nNSpid: 711 9",
        "Pid: -1\nNSpid: -1",
        "Pid: 710\nPid: 710\nNSpid: 710 9",
    ],
)
def test_fdinfo_refuses_conflicting_or_dead_identity(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    monkeypatch.setattr(linux.Path, "read_text", lambda *args, **kwargs: raw)
    with pytest.raises(linux.LinuxControlError):
        linux._pidfd_pids(42)


def test_ephemeral_identifier_is_rejected_by_durable_reopen() -> None:
    name = "linux-pidns-ephemeral-v1:" + "a" * 32 + ":700:33:44:55"
    assert linux._valid_ephemeral_tree(name, "a" * 32)
    assert not linux.validate_tree_id(name, "a" * 32)
    with pytest.raises(linux.LinuxControlError):
        linux.reopen(
            dict(
                schema_version=1,
                pid=700,
                birth_id="linux-start:" + "a" * 36 + ":33",
                job_name=name,
                identity={},
            ),
            pid=700,
            identity={},
        )


@pytest.mark.parametrize("option", ["token", "receipt_path", "identity"])
def test_independent_durable_inputs_refuse_before_launch(
    monkeypatch: pytest.MonkeyPatch, option: str
) -> None:
    monkeypatch.setattr(linux, "inherited", lambda env: None)
    options: dict[str, Any] = {option: {}}
    with pytest.raises(
        linux.LinuxControlError, match="linux_ephemeral_durable_inputs_unsupported"
    ):
        linux.spawn(["must-not-execute"], independent=True, **options)


def test_independent_flag_requires_boolean() -> None:
    with pytest.raises(TypeError, match="independent must be a bool"):
        native.spawn_owned(["must-not-execute"], independent="yes")  # type: ignore[arg-type]


def test_helper_and_native_regression_scripts_compile() -> None:
    for name, source in (
        ("helper", linux._HELPER),
        ("supervisor", _SUPERVISOR),
        ("target", _TARGET),
        ("nested", _NESTED),
    ):
        compile(source, "<" + name + ">", "exec", dont_inherit=True)


@pytest.mark.skipif(
    os.name != "nt" and not sys.platform.startswith("linux"),
    reason="Owned execution platform",
)
def test_unknown_option_refuses_before_target(tmp_path: Path) -> None:
    marker = tmp_path / "must-not-exist"
    with pytest.raises(TypeError):
        native.spawn_owned(
            [
                sys.executable,
                "-B",
                "-c",
                "import pathlib,sys;pathlib.Path(sys.argv[1]).touch()",
                str(marker),
            ],
            independent=True,
            unknown_launch_option=True,
        )
    assert not marker.exists()


@pytest.mark.skipif(os.name != "nt", reason="Real Windows Job regression")
def test_windows_independent_retains_real_job_and_stdlib_wait() -> None:
    process = native.spawn_owned(
        [sys.executable, "-B", "-c", "import time; time.sleep(60)"],
        independent=True,
    )
    job = getattr(process, "native_job")
    try:
        assert isinstance(job, native.OwnedJob)
        assert process.pid == getattr(process, "native_facts")["pid"]
        assert job.active() == 1
        assert job.stop(deadline=time.monotonic() + 5)
        assert process.wait(timeout=5) == 130
        assert job.active() == 0
    finally:
        if process.poll() is None:
            job.stop(deadline=time.monotonic() + 5)
            process.wait(timeout=5)
        job.close()


_SUPERVISOR = r"""
import os, subprocess, sys
import pf_linux_native_control as linux
from pf_native_control import spawn_owned
assert linux.inherited(dict(os.environ))["job_name"].startswith("linux-pidns-ephemeral-v1:")
ordinary = spawn_owned([sys.executable, "-B", "-c", "pass"])
assert not hasattr(ordinary, "native_job")
assert ordinary.wait(timeout=5) == 0
# A deeper ephemeral launch exercises another NSpid depth with the same procfs.
deeper = spawn_owned([sys.executable, "-B", "-c", "pass"], independent=True)
try:
    assert deeper.wait(timeout=5) == 0
    assert deeper.native_job.active() == 0
finally:
    deeper.native_job.close()
writer = int(sys.argv[1])
target = subprocess.Popen(sys.argv[2:])
code = target.wait()
os.write(writer, (str(code) + "\n").encode("ascii"))
os.close(writer)
"""

_TARGET = r"""
import json, os, pathlib, signal, sys, time
marker, outcome = pathlib.Path(sys.argv[1]), sys.argv[2]
if os.fork() == 0:
    os.setsid()
    raw = pathlib.Path("/proc/self/status").read_text()
    visible = int(raw.split("NSpid:")[1].split()[0])
    marker.write_text(json.dumps({"pid": visible, "pidns": os.readlink("/proc/self/ns/pid")}))
    time.sleep(60)
while not marker.exists():
    time.sleep(0.01)
if outcome == "timeout":
    time.sleep(60)
if outcome == "signal":
    os.kill(os.getpid(), signal.SIGTERM)
os._exit(17 if outcome == "nonzero" else 0)
"""

_NESTED = r"""
import json, os, pathlib, select, subprocess, sys, time
import pf_linux_native_control as linux
from pf_native_control import spawn_owned, reopen_job
root, outcome, supervisor, target = pathlib.Path(sys.argv[1]), *sys.argv[2:]
original = linux.inherited(dict(os.environ))
assert original is not None
outer_fd = os.pidfd_open(os.getpid())
outer_namespace = os.readlink("/proc/self/ns/pid")
try:
    # Default ordinary nesting still has no independent owner and keeps membership,
    # including when the caller supplies a replacement environment.
    ordinary = spawn_owned([sys.executable, "-B", "-c",
        "import os,sys;assert os.readlink('/proc/self/ns/pid')==sys.argv[1]", outer_namespace],
        env={})
    assert not hasattr(ordinary, "native_job")
    assert ordinary.wait(timeout=5) == 0
    for options in ({"token": "a"*32}, {"receipt_path": root/"forbidden"}, {"identity": {}}):
        try:
            spawn_owned([sys.executable, "-c", "raise AssertionError('target entered')"],
                        independent=True, **options)
        except linux.LinuxControlError as error:
            assert error.reason == "linux_ephemeral_durable_inputs_unsupported"
        else:
            raise AssertionError("durable nested input accepted")
    marker = root / "descendant.json"
    if outcome.startswith("before-go"):
        launched = []
        popen, retain = linux.subprocess.Popen, linux._retain_ephemeral
        mapping, readlink = linux._pidfd_pids, linux.os.readlink
        def capture(*args, **kwargs):
            process = popen(*args, **kwargs)
            launched.append(process)
            return process
        def refuse(*args, **kwargs):
            raise PermissionError(13, "fixture proof denied")
        linux.subprocess.Popen = capture
        if outcome == "before-go":
            linux._retain_ephemeral = refuse
        elif outcome == "before-go-mapping":
            def changed_mapping(fd):
                pids = mapping(fd)
                return (pids[0] + 1, *pids[1:])
            linux._pidfd_pids = changed_mapping
        else:
            linux.os.readlink = lambda path: (
                outer_namespace if str(path).endswith("/ns/pid_for_children") else readlink(path))
        try:
            try:
                spawn_owned([sys.executable, "-B", "-c", target, str(marker), "success"], independent=True)
            except OSError as error:
                if outcome == "before-go":
                    assert isinstance(error, PermissionError) and error.errno == 13
                else:
                    assert isinstance(error, linux.LinuxControlError)
                    assert error.reason == (
                        "linux_pidfd_mapping_mismatch" if outcome == "before-go-mapping"
                        else "linux_independent_namespace_mismatch")
            else:
                raise AssertionError("proof denial entered target")
            assert len(launched) == 1 and launched[0].poll() is not None
            assert not marker.exists()
        finally:
            linux.subprocess.Popen, linux._retain_ephemeral = popen, retain
            linux._pidfd_pids, linux.os.readlink = mapping, readlink
    else:
        reader, writer = os.pipe()
        process = None
        descendant_fd = None
        try:
            process = spawn_owned(
                [sys.executable, "-B", "-c", supervisor, str(writer),
                 sys.executable, "-B", "-c", target, str(marker),
                 "timeout" if outcome == "carrier-death" else outcome],
                independent=True, pass_fds=(writer,))
            job = process.native_job
            os.close(writer)
            writer = None
            facts = process.native_facts
            assert facts["job_name"].startswith("linux-pidns-ephemeral-v1:")
            depth = len(linux._self_pids()) - 1
            assert linux._pidfd_pids(job.carrier)[depth] == process.pid
            assert depth >= 1  # procfs is mounted in the ancestor, even if numbers coincide.
            assert job.active() == 1
            try:
                reopen_job(facts, pid=facts["pid"], identity={})
            except linux.LinuxControlError:
                pass
            else:
                raise AssertionError("ephemeral facts reopened as durable")
            deadline = time.monotonic() + 8
            while not marker.exists():
                assert time.monotonic() < deadline
                time.sleep(0.01)
            child = json.loads(marker.read_text())
            assert child["pidns"] != outer_namespace
            proc_pid = child["pid"]
            pids = linux._pid_numbers(pathlib.Path(f"/proc/{proc_pid}/status").read_text(), "NSpid")
            descendant_fd = linux._retain_ephemeral(pids[depth], proc_pid, linux._ticks(proc_pid))
            ready = bool(select.select([reader], [], [], 0.3 if outcome in {"timeout", "carrier-death"} else 8)[0])
            if outcome in {"timeout", "carrier-death"}:
                assert not ready
            else:
                assert ready
                code = int(os.read(reader, 32))
                assert code == {"success": 0, "nonzero": 17, "signal": -15}[outcome]
            assert process.poll() is None  # Carrier lifetime still covers all descendants.
            if outcome == "carrier-death":
                process.kill()
            assert job.stop(deadline=time.monotonic() + 5)
            process.wait(timeout=5)  # Local Popen PID remains correct for waitpid.
            assert job.active() == 0
            assert select.select([descendant_fd], [], [], 0)[0]
        finally:
            os.close(reader)
            if writer is not None:
                os.close(writer)
            if descendant_fd is not None:
                os.close(descendant_fd)
            if process is not None:
                process.native_job.stop(deadline=time.monotonic() + 5)
                process.wait(timeout=5)
                process.native_job.close()
    assert not select.select([outer_fd], [], [], 0)[0]
    assert linux.inherited(dict(os.environ)) == original
    assert os.readlink("/proc/self/ns/pid") == outer_namespace
    print(json.dumps({"outcome": outcome, "outer_alive": True}), flush=True)
finally:
    os.close(outer_fd)
"""


@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Real Linux namespaces"
)
@pytest.mark.parametrize(
    "outcome",
    [
        "success",
        "nonzero",
        "signal",
        "timeout",
        "carrier-death",
        "before-go",
        "before-go-mapping",
        "before-go-namespace",
    ],
)
def test_nested_independent_cleanup_preserves_outer(
    tmp_path: Path, outcome: str
) -> None:
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    # Make the accepted isolated source available to the actual nested interpreter.
    environment["PYTHONPATH"] = os.pathsep.join(
        [
            str(Path(__file__).resolve().parents[2] / "tools"),
            environment.get("PYTHONPATH", ""),
        ]
    )
    outer = native.spawn_owned(
        [
            sys.executable,
            "-B",
            "-c",
            _NESTED,
            str(tmp_path),
            outcome,
            _SUPERVISOR,
            _TARGET,
        ],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    owner = getattr(outer, "native_job")
    try:
        stdout, stderr = outer.communicate(timeout=25)
        assert outer.returncode == 0, stderr.decode(errors="replace")
        assert json.loads(stdout) == {"outcome": outcome, "outer_alive": True}
        assert owner.active() == 0
    finally:
        owner.stop(deadline=time.monotonic() + 5)
        outer.wait(timeout=5)
        owner.close()
