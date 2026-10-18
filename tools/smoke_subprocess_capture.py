#!/usr/bin/env python3
"""Exercise real output capture and timeout cleanup in a UTF-8 interpreter."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


WRAPPER = """
import json, sys
from dataclasses import asdict
sys.path.insert(0, sys.argv[1])
from processforge_subprocess import run_command
try:
    result = run_command([sys.executable, '-c', sys.argv[2]],
                         timeout=float(sys.argv[3]), check=sys.argv[4] == 'check')
except RuntimeError as exc:
    print(json.dumps({'error': str(exc)}))
else:
    print(json.dumps(asdict(result)))
"""


def capture(child: str, *, timeout: float = 5, check: bool = False) -> dict:
    result = subprocess.run(
        [sys.executable, "-B", "-X", "utf8", "-c", WRAPPER,
         str(Path(__file__).resolve().parent), child, str(timeout),
         "check" if check else "result"],
        env=dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not result.stderr, result.stderr  # Includes failures in Popen reader threads.
    return json.loads(result.stdout)


def process_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetExitCodeProcess.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            assert ctypes.get_last_error() == 87, "Unable to inspect our timed-out child"
            return False
        try:
            code = wintypes.DWORD()
            assert kernel.GetExitCodeProcess(handle, ctypes.byref(code))
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def main() -> int:
    invalid = capture("import os;os.write(1,b'out:'+b'\\x93'+b':end\\n');os.write(2,b'err:'+b'\\xff'+b':end\\n')")
    assert invalid["stdout"] == "out:" + "\ufffd:end\n", invalid
    assert invalid["stderr"] == "err:" + "\ufffd:end\n", invalid
    assert invalid["returncode"] == 0 and not invalid["timed_out"], invalid

    valid = capture("import os;os.write(1,'alpha \\u03b1\\r\\n'.encode());os.write(2,'beta \\u03b2\\n'.encode())")
    assert valid["stdout"] == "alpha \u03b1\n" and valid["stderr"] == "beta \u03b2\n", valid
    assert valid["returncode"] == 0 and not valid["timed_out"], valid
    assert valid["timeout_seconds"] == 5 and valid["cwd"] is None and valid["label"] is None, valid

    failure = "import sys;print('out');print('err',file=sys.stderr);sys.exit(7)"
    nonzero = capture(failure)
    assert nonzero["returncode"] == 7 and not nonzero["timed_out"], nonzero
    assert nonzero["stdout"] == "out\n" and nonzero["stderr"] == "err\n", nonzero
    checked = capture(failure, check=True)
    newline = "\n"
    assert all(part in checked["error"] for part in ["Exit code:" + newline + "  7", "STDOUT tail:" + newline, "STDERR tail:" + newline]), checked

    timed = capture("import os,time;print(os.getpid(),flush=True);time.sleep(60)", timeout=0.5)
    assert timed["timed_out"] and timed["returncode"] not in (None, 0), timed
    assert timed["stdout"].strip(), timed
    pid = int(timed["stdout"].splitlines()[0])
    assert not process_alive(pid), "Timed-out child survived cleanup"
    print("PASS: subprocess capture (malformed streams, Unicode, nonzero, check, timeout cleanup)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
