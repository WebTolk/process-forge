"""Scoped mocked Linux adapter checks; these do not prove real X11 behavior."""

from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
import sys
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


SOURCE = Path(__file__).resolve().parents[4] / "tools/pf_runtime/linux_console.py"
SPEC = importlib.util.spec_from_file_location("pf_linux_console_under_test", SOURCE)
linux = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = linux
SPEC.loader.exec_module(linux)

ENVIRONMENT = {"DISPLAY": ":0", "WINDOWID": "0x2a", "XDG_SESSION_TYPE": "x11", "TERM": "xterm-256color"}
NORMAL = '''_NET_WM_PID(CARDINAL) = 100
WM_CLASS(STRING) = "pf-server", "XTerm"
WM_STATE(WM_STATE):
        window state: Normal
        icon window: 0x0
_NET_WM_STATE(ATOM) = _NET_WM_STATE_FOCUSED
'''
MINIMIZED = NORMAL.replace("state: Normal", "state: Iconic").replace("_NET_WM_STATE_FOCUSED", "_NET_WM_STATE_HIDDEN")
TERMINAL = linux._Terminal(42, 200, 100, 1234, 1024)


@contextmanager
def adapter_environment(changes=None):
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, {**ENVIRONMENT, **(changes or {})}, clear=True))
        stack.enter_context(patch.object(sys, "platform", "linux"))
        for name, fd in (("stdin", 0), ("stdout", 1)):
            stack.enter_context(patch.object(sys, name, Mock(isatty=Mock(return_value=True), fileno=Mock(return_value=fd))))
        yield stack


@contextmanager
def owned_environment():
    with adapter_environment() as stack:
        calls = {}
        replacements = {
            "getpid": 200, "getppid": 100, "getpgrp": 200, "getsid": 200,
            "tcgetpgrp": 200, "getuid": 1000, "geteuid": 1000,
        }
        for name, result in replacements.items():
            calls[name] = stack.enter_context(patch.object(linux.os, name, return_value=result, create=True))
        calls["fstat"] = stack.enter_context(patch.object(linux.os, "fstat", return_value=SimpleNamespace(st_mode=stat.S_IFCHR, st_rdev=1024)))
        calls["stat"] = stack.enter_context(patch.object(Path, "stat", return_value=SimpleNamespace(st_uid=1000)))
        calls["resolve"] = stack.enter_context(patch.object(Path, "resolve", return_value=Path("/usr/bin/xterm")))
        calls["samefile"] = stack.enter_context(patch.object(Path, "samefile", return_value=True))
        calls["read_bytes"] = stack.enter_context(patch.object(Path, "read_bytes", return_value=b"xterm\0-e\0python3\0bin/pf.py\0serve\0"))
        calls["read_text"] = stack.enter_context(patch.object(Path, "read_text", return_value="200 "))
        calls["which"] = stack.enter_context(patch.object(linux.shutil, "which", return_value="/usr/bin/python3"))
        calls["process_stat"] = stack.enter_context(patch.object(linux, "_process_stat", side_effect=lambda pid: (100, 700) if pid == 200 else (1, 1234)))
        calls["exclusive_terminal"] = stack.enter_context(patch.object(linux, "_exclusive_terminal", return_value=True))
        yield calls


class EnvironmentChecks(unittest.TestCase):
    def test_refused_environments_do_not_inspect_or_mutate_windows(self):
        cases = [
            ({"WAYLAND_DISPLAY": "wayland-0"}, "unsupported"),
            ({"XDG_SESSION_TYPE": "wayland"}, "unsupported"),
            ({"XDG_SESSION_TYPE": "tty"}, "unsupported"),
            ({"DISPLAY": ""}, "unavailable"),
            ({"DISPLAY": "localhost:10.0"}, "unavailable"),
            ({"DISPLAY": "host:0"}, "unavailable"),
            ({"TERM": "screen-256color"}, "unavailable"),
            ({"TERM": "tmux-256color"}, "unavailable"),
        ]
        cases.extend(({name: "present"}, "unavailable") for name in (
            "SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY", "TMUX", "STY", "ZELLIJ", "ZELLIJ_SESSION_NAME",
        ))
        for environment, expected in cases:
            with self.subTest(environment=environment), adapter_environment(environment):
                with patch.object(linux, "_owned_terminal") as owned, patch.object(linux, "_run") as run:
                    self.assertEqual(linux.minimize_console(), expected)
                    owned.assert_not_called()
                    run.assert_not_called()

    def test_other_platform_is_unsupported(self):
        with patch.object(sys, "platform", "win32"), patch.object(linux, "_run") as run:
            self.assertEqual(linux.minimize_console(), "unsupported")
            run.assert_not_called()

    def test_none_redirected_or_closed_streams_are_unavailable(self):
        for name in ("stdin", "stdout"):
            for stream in (None, Mock(isatty=Mock(return_value=False)), Mock(isatty=Mock(side_effect=ValueError))):
                with self.subTest(name=name, stream=stream), adapter_environment():
                    with patch.object(sys, name, stream), patch.object(linux, "_run") as run:
                        self.assertEqual(linux.minimize_console(), "unavailable")
                        run.assert_not_called()

    def test_window_id_is_only_an_exact_32_bit_numeric_id(self):
        for value in ("", "0", "-1", "42;bad", "$(bad)", " 42", "42\n", "0x100000000", "4294967296", "1" * 100):
            with self.subTest(value=value), adapter_environment({"WINDOWID": value}):
                with patch.object(linux, "_owned_terminal") as owned, patch.object(linux, "_run") as run:
                    self.assertEqual(linux.minimize_console(), "not_owned")
                    owned.assert_not_called()
                    run.assert_not_called()
        self.assertEqual(linux._window_id("42"), 42)
        self.assertEqual(linux._window_id("0x2a"), 42)
        self.assertEqual(linux._window_id("4294967295"), 0xFFFFFFFF)


class OwnershipChecks(unittest.TestCase):
    def test_direct_dedicated_xterm_passes_process_checks(self):
        with owned_environment():
            self.assertEqual(linux._owned_terminal(42), TERMINAL)

    def test_non_xterm_shell_embed_shared_session_or_identity_is_refused(self):
        cases = [
            ("resolve", Path("/usr/bin/gnome-terminal-server")),
            ("samefile", False),
            ("which", None),
            ("read_bytes", b"xterm\0"),
            ("read_bytes", b"xterm\0-e\0"),
            ("read_bytes", b"xterm\0-into\0999\0-e\0python3\0"),
            ("read_bytes", b"xterm\0-Scc5\0-e\0python3\0"),
            ("read_text", "200 201"),
            ("read_text", "201"),
            ("getpgrp", 50),
            ("getsid", 50),
            ("tcgetpgrp", 201),
            ("getuid", 2000),
            ("stat", SimpleNamespace(st_uid=2000)),
            ("fstat", SimpleNamespace(st_mode=stat.S_IFREG, st_rdev=1024)),
            ("exclusive_terminal", False),
        ]
        for method, result in cases:
            with self.subTest(method=method, result=result), owned_environment() as calls:
                calls[method].return_value = result
                self.assertIsNone(linux._owned_terminal(42))

    def test_different_input_output_terminals_are_refused(self):
        with owned_environment() as calls:
            calls["fstat"].side_effect = [
                SimpleNamespace(st_mode=stat.S_IFCHR, st_rdev=1024),
                SimpleNamespace(st_mode=stat.S_IFCHR, st_rdev=1025),
            ]
            self.assertIsNone(linux._owned_terminal(42))

    def test_parent_change_and_pid_reuse_are_refused(self):
        with owned_environment() as calls:
            calls["getppid"].side_effect = [100, 101]
            self.assertIsNone(linux._owned_terminal(42))
        with owned_environment() as calls:
            calls["process_stat"].side_effect = [(100, 700), (1, 1234), (1, 1235)]
            self.assertIsNone(linux._owned_terminal(42))
        with owned_environment() as calls:
            calls["process_stat"].side_effect = [(101, 700), (1, 1234)]
            self.assertIsNone(linux._owned_terminal(42))

    def test_proc_stat_allows_parentheses_in_process_name(self):
        fields = ["S", "100"] + ["0"] * 17 + ["1234"]
        with patch.object(Path, "read_text", return_value="200 (python (worker)) " + " ".join(fields)):
            self.assertEqual(linux._process_stat(200), (100, 1234))


class ExclusiveTerminalChecks(unittest.TestCase):
    @contextmanager
    def proc_view(self, others=None, names=None):
        own = ["S", "100", "200", "200", "1024"]
        fields_by_pid = {200: own, 100: ["S", "1", "100", "100", "0"], **(others or {})}
        entries = [SimpleNamespace(name=name) for name in (names or ["self", "net", "100", "200", *map(str, (others or {}))])]
        with ExitStack() as stack:
            fields = stack.enter_context(patch.object(linux, "_process_fields", side_effect=lambda pid: fields_by_pid[pid]))
            scan = stack.enter_context(patch.object(linux.os, "scandir"))
            scan.return_value.__enter__.return_value = iter(entries)
            stack.enter_context(patch.object(linux.os, "major", return_value=4, create=True))
            stack.enter_context(patch.object(linux.os, "minor", return_value=0, create=True))
            yield fields

    def test_only_our_process_in_session_and_terminal_is_accepted(self):
        with self.proc_view():
            self.assertTrue(linux._exclusive_terminal(200, 1024))

    def test_shared_session_or_tty_is_refused_even_after_reparenting(self):
        for other in (["S", "1", "300", "200", "0"], ["S", "1", "300", "300", "1024"]):
            with self.subTest(other=other), self.proc_view({300: other}):
                self.assertFalse(linux._exclusive_terminal(200, 1024))

    def test_missing_controlling_tty_or_mismatched_device_is_refused(self):
        for own in (["S", "100", "200", "200", "0"], ["S", "100", "200", "200", "1025"], ["S", "100", "200", "201", "1024"]):
            with self.subTest(own=own), self.proc_view() as fields:
                fields.side_effect = lambda pid: own
                self.assertFalse(linux._exclusive_terminal(200, 1024))

    def test_high_minor_device_bits_are_encoded(self):
        with self.proc_view() as fields, patch.object(linux.os, "major", return_value=136), patch.object(linux.os, "minor", return_value=257):
            fields.side_effect = lambda pid: ["S", "100", "200", "200", str(0x108801)] if pid == 200 else ["S", "1", "100", "100", "0"]
            self.assertTrue(linux._exclusive_terminal(200, 1024))

    def test_disappearing_process_is_skipped_but_unreadable_proc_is_not(self):
        for error in (FileNotFoundError, PermissionError):
            with self.subTest(error=error), self.proc_view(names=["300"]) as fields:
                fields.side_effect = [["S", "100", "200", "200", "1024"], error]
                if error is FileNotFoundError:
                    self.assertTrue(linux._exclusive_terminal(200, 1024))
                else:
                    with self.assertRaises(PermissionError):
                        linux._exclusive_terminal(200, 1024)

    def test_scan_count_and_time_are_bounded(self):
        with self.proc_view(names=["self"] * 5), patch.object(linux, "_PROCESS_SCAN_LIMIT", 4):
            self.assertFalse(linux._exclusive_terminal(200, 1024))
        with self.proc_view(), patch.object(linux.time, "monotonic", side_effect=[10.0, 11.0]):
            self.assertFalse(linux._exclusive_terminal(200, 1024))
        with self.proc_view(names=["self"]), patch.object(linux.time, "monotonic", side_effect=[10.0, 10.1, 11.0]):
            self.assertFalse(linux._exclusive_terminal(200, 1024))


class MinimizationChecks(unittest.TestCase):
    @contextmanager
    def backend(self, properties=None):
        with adapter_environment() as stack:
            owned = stack.enter_context(patch.object(linux, "_owned_terminal", return_value=TERMINAL))
            which = stack.enter_context(patch.object(linux.shutil, "which", side_effect=lambda name: "/usr/bin/" + name))
            props = stack.enter_context(patch.object(linux, "_properties", side_effect=properties or [NORMAL, MINIMIZED]))
            run = stack.enter_context(patch.object(linux, "_run", return_value=SimpleNamespace(returncode=0)))
            stack.enter_context(patch.object(linux.time, "sleep"))
            yield owned, which, props, run

    def test_success_requires_observed_iconic_and_hidden_on_owned_window(self):
        with self.backend([NORMAL, NORMAL, MINIMIZED]) as (_, _, props, run):
            self.assertEqual(linux.minimize_console(), "minimized")
            self.assertEqual(props.call_count, 3)
            run.assert_called_once_with(["/usr/bin/xdotool", "windowminimize", "42"])

    def test_unconfirmed_or_partial_state_is_failed(self):
        for properties in (NORMAL, NORMAL.replace("state: Normal", "state: Iconic"), NORMAL.replace("_NET_WM_STATE_FOCUSED", "_NET_WM_STATE_HIDDEN")):
            with self.subTest(properties=properties), self.backend([NORMAL] + [properties] * linux._STATE_CHECKS) as (_, _, props, run):
                self.assertEqual(linux.minimize_console(), "failed")
                self.assertEqual(props.call_count, 1 + linux._STATE_CHECKS)
                run.assert_called_once()

    def test_foreign_pid_or_class_is_not_owned_and_never_mutated(self):
        for properties in (NORMAL.replace("= 100", "= 101"), NORMAL.replace("XTerm", "OtherTerm"), "WM_STATE: not found"):
            with self.subTest(properties=properties), self.backend([properties]) as (_, _, _, run):
                self.assertEqual(linux.minimize_console(), "not_owned")
                run.assert_not_called()

    def test_missing_or_unmanaged_initial_window_state_prevents_request(self):
        for properties in (NORMAL.replace("state: Normal", "state: Withdrawn"), NORMAL.replace("WM_STATE(WM_STATE):", "WM_STATE: not found")):
            with self.subTest(properties=properties), self.backend([properties]) as (_, _, _, run):
                self.assertEqual(linux.minimize_console(), "unavailable")
                run.assert_not_called()

    def test_ownership_change_prevents_request_or_success(self):
        with self.backend() as (owned, _, _, run):
            owned.side_effect = [TERMINAL, None]
            self.assertEqual(linux.minimize_console(), "not_owned")
            run.assert_not_called()
        with self.backend() as (owned, _, _, run):
            owned.side_effect = [TERMINAL, TERMINAL, None]
            self.assertEqual(linux.minimize_console(), "not_owned")
            run.assert_called_once()
        with self.backend([NORMAL, MINIMIZED.replace("= 100", "= 101")]):
            self.assertEqual(linux.minimize_console(), "not_owned")

    def test_missing_tools_and_unreadable_window_are_unavailable(self):
        for name in ("xprop", "xdotool"):
            with self.subTest(tool=name), self.backend() as (_, which, _, run):
                which.side_effect = lambda requested: None if requested == name else "/usr/bin/" + requested
                self.assertEqual(linux.minimize_console(), "unavailable")
                run.assert_not_called()
        with self.backend([None]) as (_, _, _, run):
            self.assertEqual(linux.minimize_console(), "unavailable")
            run.assert_not_called()

    def test_missing_process_access_fails_closed(self):
        with self.backend() as (owned, _, _, run):
            owned.side_effect = PermissionError
            self.assertEqual(linux.minimize_console(), "unavailable")
            run.assert_not_called()

    def test_command_failure_and_timeout_do_not_report_success(self):
        with self.backend() as (_, _, _, run):
            run.return_value.returncode = 1
            self.assertEqual(linux.minimize_console(), "failed")
        with self.backend() as (_, _, _, run):
            run.side_effect = subprocess.TimeoutExpired("xdotool", 1)
            self.assertEqual(linux.minimize_console(), "failed")
        with self.backend([NORMAL, None]):
            self.assertEqual(linux.minimize_console(), "failed")
        with self.backend() as (_, _, props, run):
            props.side_effect = subprocess.TimeoutExpired("xprop", 1)
            self.assertEqual(linux.minimize_console(), "failed")
            run.assert_not_called()

    def test_already_minimized_requires_ownership_and_avoids_another_request(self):
        with self.backend([MINIMIZED]) as (owned, _, _, run):
            self.assertEqual(linux.minimize_console(), "minimized")
            self.assertEqual(owned.call_count, 2)
            run.assert_not_called()

    def test_subprocess_calls_are_bounded_and_do_not_use_a_shell(self):
        with patch.object(linux.subprocess, "run") as run:
            linux._run(["xprop", "-id", "42", "_NET_WM_PID"])
            arguments, options = run.call_args
            self.assertEqual(arguments, (["xprop", "-id", "42", "_NET_WM_PID"],))
            self.assertIs(options["shell"], False)
            self.assertEqual(options["timeout"], 1.0)
            self.assertEqual(options["stdin"], subprocess.DEVNULL)
            self.assertEqual(options["env"]["LC_ALL"], "C")
        with patch.object(linux, "_run", return_value=SimpleNamespace(returncode=1)):
            self.assertIsNone(linux._properties("xprop", 42))

    def test_import_has_no_desktop_or_process_inspection_side_effects(self):
        spec = importlib.util.spec_from_file_location("pf_linux_console_import_check", SOURCE)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            with ExitStack() as stack:
                mocks = [stack.enter_context(patch.object(owner, name, side_effect=AssertionError("import-time I/O")))
                         for owner, name in ((subprocess, "run"), (linux.shutil, "which"),
                                             (Path, "read_text"), (Path, "read_bytes"), (Path, "stat"),
                                             (linux.os, "getpid"), (linux.os, "fstat"))]
                spec.loader.exec_module(module)
                for mocked in mocks:
                    mocked.assert_not_called()
        finally:
            del sys.modules[spec.name]


if __name__ == "__main__":
    unittest.main(verbosity=2)
