"""Human console presentation for the foreground App Server."""

from __future__ import annotations

import os
import sys


def minimize_console() -> str:
    """Request minimization through a lazy adapter for an owned GUI console."""
    if any(os.environ.get(name) for name in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY", "TMUX", "STY")):
        return "unavailable"
    try:
        if sys.platform == "win32":
            from .windows_console import minimize_console as minimize
        elif sys.platform == "linux":
            from .linux_console import minimize_console as minimize
        else:
            return "unsupported"
        return minimize()
    except Exception:
        # Optional desktop integration must not prevent the service from starting.
        return "failed"


def show_server_console(core_version: str, *, minimized: bool = False) -> None:
    """Identify a foreground server on a TTY, leaving redirected streams clean."""
    stream = sys.stdout
    try:
        if stream is None or not stream.isatty():
            return
    except (AttributeError, OSError, ValueError):
        return

    try:
        from .monitor import banner

        logo = "\n".join(banner(False))
        try:
            logo.encode(stream.encoding or "ascii")
        except (UnicodeEncodeError, LookupError):
            logo = "\n".join(banner(True))
        print(logo, file=stream)
        print(f"App Server Core {core_version or 'unknown'} | PID {os.getpid()}", file=stream)
        print("Foreground Runtime: closing this window stops the server.", file=stream)
        print("The monitor opens separately; closing the monitor leaves the server running.", file=stream, flush=True)

        if minimized:
            result = minimize_console()
            if result != "minimized":
                messages = {
                    "not_owned": "this terminal is shared or is not an owned server window",
                    "unsupported": "this desktop or terminal cannot minimize an owned server window",
                    "unavailable": "a local dedicated GUI console is unavailable",
                    "failed": "the desktop did not confirm minimization",
                }
                reason = messages.get(result, messages["failed"])
                print(f"Window remains visible: {reason}. Server startup continues.", file=stream, flush=True)
    except (OSError, ValueError):
        # A lost or closed TTY only disables optional presentation, not serve().
        return
