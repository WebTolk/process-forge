"""Preserve capability lookup timing at the terminal context boundary."""

import io
import sys
from types import SimpleNamespace

import pytest
from pf_runtime import monitor


class Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True

    def fileno(self) -> int:
        return 3


def test_cleanup_uses_live_function_and_drain(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int]] = []
    previous: list[object] = [1, 2, 3]
    term = SimpleNamespace(
        tcgetattr=lambda fd: previous,
        tcsetattr=lambda fd, drain, state: calls.append(("original", drain)),
        TCSADRAIN=2,
    )
    monkeypatch.setattr(monitor, "os", SimpleNamespace(name="posix", environ={}))
    monkeypatch.setitem(sys.modules, "termios", term)
    monkeypatch.setitem(sys.modules, "tty", SimpleNamespace(setcbreak=lambda fd: None))
    stream = Terminal()
    with monitor.terminal_mode(stream, stream):
        term.tcsetattr = lambda fd, drain, state: calls.append(("override", drain))
        term.TCSADRAIN = 7
    assert calls == [("override", 7)]


@pytest.mark.parametrize(
    "missing", ["tcsetattr", "TCSADRAIN", "tcgetattr", "setcbreak"]
)
def test_missing_capability_effect_order(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    calls: list[str] = []

    def get_attributes(fd: int) -> list[object]:
        calls.append("get")
        return []

    term = SimpleNamespace(
        tcgetattr=get_attributes,
        tcsetattr=lambda *args: calls.append("set"),
        TCSADRAIN=2,
    )
    tty = SimpleNamespace(setcbreak=lambda fd: calls.append("cbreak"))
    delattr(tty if missing == "setcbreak" else term, missing)
    monkeypatch.setattr(monitor, "os", SimpleNamespace(name="posix", environ={}))
    monkeypatch.setitem(sys.modules, "termios", term)
    monkeypatch.setitem(sys.modules, "tty", tty)
    stream = Terminal()
    with pytest.raises(AttributeError):
        with monitor.terminal_mode(stream, stream):
            calls.append("body")
    expected = {
        "tcgetattr": [],
        "setcbreak": ["get", "set"],
        "tcsetattr": ["get", "cbreak", "body"],
        "TCSADRAIN": ["get", "cbreak", "body"],
    }
    assert calls == expected[missing]
    if missing != "tcgetattr":
        assert stream.getvalue().endswith("\x1b[?25h\x1b[?1049l")
