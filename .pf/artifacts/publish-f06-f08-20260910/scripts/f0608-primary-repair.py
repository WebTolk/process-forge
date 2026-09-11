from pathlib import Path
p=Path('tools/processforge.py');s=p.read_text(encoding='utf-8')
a=s.index('def _registry_lock_write(');b=s.index('def _registry_lock_owner_alive(',a);s=s[:a]+s[b:]
s=s.replace('            handle = kernel32.OpenProcess(0x1000, False, pid)', '''            from ctypes import wintypes
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            handle = kernel32.OpenProcess(0x1000, False, pid)''')
a=s.index('def _registry_lock_owner_alive(');b=s.index('def _registry_lock_stale(',a)
s=s[:a]+s[a:b].replace('    except OSError:\n        return False','    except OSError:\n        return True')+s[b:]
a=s.index('def _registry_lock_reap_if_stale(');b=s.index('def parse_cli_bool(',a)
s=s[:a]+'''def _registry_lock_read_owner(lock_path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


@contextlib.contextmanager
def registry_file_lock(path: Path, *, timeout_seconds: float = 30.0, stale_after_seconds: float = 300.0) -> Any:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    # Never unlink this guard: all new writers and stale-owner recovery must
    # lock the same inode, including across Windows close-before-unlink.
    guard_path = path.with_name(f".{path.name}.lock.guard")
    guard_fd = os.open(str(guard_path), os.O_CREAT | os.O_RDWR, 0o600)
    deadline = time.monotonic() + timeout_seconds
    owner = {"path": str(path), "pid": os.getpid(), "host": platform.node(),
             "created_at": now_utc(), "token": uuid.uuid4().hex}
    acquired = False

    def wait_for_owner() -> None:
        if time.monotonic() >= deadline:
            raise SystemExit(f"FAIL: registry is locked by another writer: {lock_path}")
        time.sleep(0.1)

    try:
        while not _registry_lock_try_os_lock(guard_fd):
            wait_for_owner()
        while True:
            try:
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                existing = _registry_lock_read_owner(lock_path)
                if (existing and _registry_lock_stale(existing, lock_path, stale_after_seconds)
                        and _registry_lock_owner_alive(existing) is False):
                    # The persistent guard serializes reapers with acquisition
                    # and release. Unknown/foreign/live legacy owners stay put.
                    if _registry_lock_read_owner(lock_path) == existing:
                        try:
                            lock_path.unlink()
                        except FileNotFoundError:
                            pass
                        continue
                wait_for_owner()
                continue
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(owner, handle, ensure_ascii=False, sort_keys=True)
                    handle.write("\\n")
                    handle.flush()
                    os.fsync(handle.fileno())
            except BaseException:
                lock_path.unlink(missing_ok=True)
                raise
            acquired = True
            break
        yield
    finally:
        try:
            if acquired and _registry_lock_read_owner(lock_path) == owner:
                lock_path.unlink(missing_ok=True)
        finally:
            os.close(guard_fd)


'''+s[b:]
p.write_text(s,encoding='utf-8')
print('Replaced unsafe close/reap protocol with a persistent OS guard; fixed Win32 handle declarations.')
