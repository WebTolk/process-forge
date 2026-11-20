"""Minimize only a dedicated, visible classic Windows console."""

from __future__ import annotations

import ctypes
import os
import sys
import time
from ctypes import wintypes
from typing import Any


def _load_api() -> tuple[Any, Any]:
    """Bind native functions on demand, without import-time desktop access."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    user = ctypes.WinDLL("user32", use_last_error=True)
    kernel.GetConsoleWindow.argtypes = []
    kernel.GetConsoleWindow.restype = wintypes.HWND
    kernel.GetConsoleProcessList.argtypes = [ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]
    kernel.GetConsoleProcessList.restype = wintypes.DWORD
    user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.GetClassNameW.restype = ctypes.c_int
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.IsWindowVisible.restype = wintypes.BOOL
    user.IsIconic.argtypes = [wintypes.HWND]
    user.IsIconic.restype = wintypes.BOOL
    user.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
    user.ShowWindowAsync.restype = wintypes.BOOL
    return kernel, user


def _console_status(kernel: Any, user: Any, window: int) -> str | None:
    """Fail closed unless this process is the console's only attached client."""
    if kernel.GetConsoleWindow() != window:
        return "not_owned"
    if not user.IsWindowVisible(window):
        # ConPTY's compatibility HWND is not a visible console window.
        return "unavailable"
    class_name = ctypes.create_unicode_buffer(64)
    if not user.GetClassNameW(window, class_name, len(class_name)):
        return "unavailable"
    if class_name.value != "ConsoleWindowClass":
        return "unsupported"
    clients = (wintypes.DWORD * 2)()
    count = kernel.GetConsoleProcessList(clients, len(clients))
    if not count:
        return "unavailable"
    # Counts exceeding the small buffer are also shared consoles; never retry
    # with a broader process list or accept a launcher as another client.
    if count != 1 or clients[0] != os.getpid():
        return "not_owned"
    return None


def minimize_console() -> str:
    """Return minimized only after observing IsIconic on an owned console.

    Shared terminals and Windows Terminal/ConPTY must remain untouched. A
    failed or unavailable desktop operation is optional for server startup.
    """
    if sys.platform != "win32":
        return "unsupported"
    if any(os.environ.get(name) for name in ("WT_SESSION", "WT_PROFILE_ID")):
        return "unsupported"
    if any(os.environ.get(name) for name in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY", "TMUX", "STY")):
        return "unavailable"
    try:
        if sys.stdout is None or not sys.stdout.isatty():
            return "unavailable"
    except (AttributeError, OSError, ValueError):
        return "unavailable"
    try:
        kernel, user = _load_api()
    except (AttributeError, OSError):
        return "unavailable"
    try:
        window = kernel.GetConsoleWindow()
        if not window:
            return "unavailable"
        status = _console_status(kernel, user, window)
        if status is not None:
            return status
        if user.IsIconic(window):
            return "minimized"
        # Async avoids waiting on the console host's UI thread. Its return
        # value confirms only a queued request, never the minimized state.
        if not user.ShowWindowAsync(window, 6):  # SW_MINIMIZE
            return "failed"
        for attempt in range(6):
            status = _console_status(kernel, user, window)
            if status is not None:
                return status
            if user.IsIconic(window):
                return "minimized"
            if attempt < 5:
                time.sleep(0.05)
        return "failed"
    except (AttributeError, OSError, ValueError, ctypes.ArgumentError):
        return "failed"
