"""Windows CPU time deltas for pinned process handles, normalized to the device."""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import time

p = argparse.ArgumentParser()
p.add_argument('--pid', type=int, action='append', required=True)
p.add_argument('--seconds', type=int, default=30)
p.add_argument('--interval', type=float, default=2)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
k = ctypes.WinDLL('kernel32', use_last_error=True)
k.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
k.OpenProcess.restype = wintypes.HANDLE
k.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
k.GetProcessTimes.restype = wintypes.BOOL
k.CloseHandle.argtypes = (wintypes.HANDLE,)
k.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))


def ticks(value):
    return (value.dwHighDateTime << 32) | value.dwLowDateTime


def read(handle):
    created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
    if not k.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(kernel), ctypes.byref(user)):
        raise ctypes.WinError(ctypes.get_last_error())
    code = wintypes.DWORD()
    if not k.GetExitCodeProcess(handle, ctypes.byref(code)):
        raise ctypes.WinError(ctypes.get_last_error())
    return ticks(created), (ticks(kernel) + ticks(user)) / 10_000_000, code.value == 259


logical = os.cpu_count() or 1
records, handles = {}, {}
started = datetime.now(timezone.utc).isoformat()
try:
    for pid in a.pid:
        handle = k.OpenProcess(0x1000, False, pid)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        handles[pid] = handle
        created, cpu, alive = read(handle)
        if not alive:
            raise RuntimeError('Process exited before sampling: ' + str(pid))
        records[pid] = {'pid': pid, 'created_filetime': created, 'initial_cpu_seconds': cpu,
                        'last_cpu_seconds': cpu, 'samples': []}
    first = previous = time.perf_counter()
    deadline = first + a.seconds
    while previous < deadline:
        time.sleep(min(a.interval, deadline - previous))
        now = time.perf_counter()
        for pid, handle in handles.items():
            created, cpu, alive = read(handle)
            if not alive or created != records[pid]['created_filetime']:
                raise RuntimeError('Pinned process ended during sampling: ' + str(pid))
            records[pid]['samples'].append({'elapsed_seconds': round(now - first, 3),
                'interval_seconds': round(now - previous, 6),
                'cpu_seconds': round(cpu - records[pid]['last_cpu_seconds'], 6),
                'device_cpu_percent': round((cpu - records[pid]['last_cpu_seconds']) / (now - previous) / logical * 100, 4)})
            records[pid]['last_cpu_seconds'] = cpu
        previous = now
    for record in records.values():
        values = [row['device_cpu_percent'] for row in record['samples']]
        record['average_device_cpu_percent'] = round((record['last_cpu_seconds'] - record['initial_cpu_seconds']) / (previous - first) / logical * 100, 4)
        record['minimum_device_cpu_percent'] = min(values)
        record['maximum_device_cpu_percent'] = max(values)
        record['median_device_cpu_percent'] = statistics.median(values)
    result = {'started_at': started, 'ended_at': datetime.now(timezone.utc).isoformat(),
              'logical_processors': logical, 'wall_seconds': round(previous - first, 3),
              'formula': 'delta process kernel+user seconds / delta wall seconds / logical CPUs * 100',
              'processes': list(records.values())}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key != 'processes'}))
    for record in records.values():
        print(json.dumps({key: value for key, value in record.items() if key != 'samples'}))
finally:
    for handle in handles.values():
        k.CloseHandle(handle)
