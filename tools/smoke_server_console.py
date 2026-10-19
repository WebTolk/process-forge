#!/usr/bin/env python3
"""Foreground presentation and conservative desktop adapters; GUI IO is mocked.

These checks do not establish native Windows/X11/Wayland desktop acceptance.
The server-operator smoke invokes this suite as part of the existing smoke gate.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager, redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import stat
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pf_runtime import console, linux_console, service, windows_console
from pf_runtime.monitor import banner


class TTY(io.StringIO):
    def __init__(self, encoding="utf-8"):
        super().__init__()
        self._encoding = encoding

    @property
    def encoding(self):
        return self._encoding

    def isatty(self):
        return True

    def write(self, value):
        # StringIO alone would silently accept a broken ASCII fallback.
        value.encode(self.encoding or "ascii")
        return super().write(value)


class PresentationChecks(unittest.TestCase):
    def test_adapter_imports_do_not_touch_the_desktop_or_scan_processes(self):
        script = '''
import ctypes, os, subprocess
from unittest.mock import patch
with patch.object(ctypes, "WinDLL", side_effect=AssertionError("native bind during import"), create=True), patch.object(subprocess, "run", side_effect=AssertionError("process during import")), patch.object(os, "scandir", side_effect=AssertionError("scan during import")):
    from pf_runtime import linux_console, windows_console
'''
        env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parent), "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, env=env, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_automatic_tty_logo_running_core_pid_and_foreground_lifecycle(self):
        for encoding, ascii_logo in (("utf-8", False), ("ascii", True), (None, True)):
            with self.subTest(encoding=encoding):
                stream = TTY(encoding)
                args = argparse.Namespace(workplace="fixture", port=1234, interval=3, console=False)
                core = SimpleNamespace(PROCESSFORGE_VERSION="test-core-987", resolve_workplace_root=Mock(return_value=Path("fixture")))
                with patch.object(service, "RuntimeProcess") as process, patch.object(console, "minimize_console") as minimize, redirect_stdout(stream):
                    def serve(port):
                        self.assertIn("App Server Core test-core-987 | PID", stream.getvalue())
                        return 17
                    process.return_value.serve.side_effect = serve
                    self.assertEqual(service.command_serve(args, core), 17)
                    process.assert_called_once_with(Path("fixture"), core, interval=3.0)
                    process.return_value.serve.assert_called_once_with(1234)
                    minimize.assert_not_called()
                text = stream.getvalue()
                self.assertIn("\n".join(banner(ascii_logo)), text)
                self.assertIn(f"App Server Core test-core-987 | PID {os.getpid()}", text)
                self.assertIn("closing this window stops the server", text)
                self.assertIn("closing the monitor leaves the server running", text)
                self.assertNotIn("\x1b", text)
                self.assertNotIn("ready", text.lower())

    def test_nontty_none_and_broken_streams_never_invoke_gui(self):
        streams = [None, io.StringIO(), SimpleNamespace(isatty=Mock(side_effect=OSError)),
                   SimpleNamespace(isatty=Mock(side_effect=ValueError)), object()]
        for stream in streams:
            with self.subTest(stream=type(stream).__name__), patch.object(sys, "stdout", stream), patch.object(console, "minimize_console") as minimize:
                console.show_server_console("test", minimized=True)
                minimize.assert_not_called()
                if isinstance(stream, io.StringIO):
                    self.assertEqual(stream.getvalue(), "")

    def test_tty_header_write_and_flush_failure_do_not_prevent_serve(self):
        core = SimpleNamespace(PROCESSFORGE_VERSION="test-core", resolve_workplace_root=Mock(return_value=Path("fixture")))
        for operation in ("write", "flush"):
            for failure in (OSError, ValueError):
                for minimized in (False, True):
                    with self.subTest(operation=operation, failure=failure.__name__, minimized=minimized):
                        stream = TTY()
                        args = argparse.Namespace(workplace="fixture", console=False, minimized=minimized)
                        with patch.object(stream, operation, side_effect=failure("unavailable TTY")), patch.object(sys, "stdout", stream), patch.object(service, "RuntimeProcess") as process, patch.object(console, "minimize_console") as minimize:
                            process.return_value.serve.return_value = 19
                            self.assertEqual(service.command_serve(args, core), 19)
                            process.return_value.serve.assert_called_once_with(0)
                            minimize.assert_not_called()

    def test_minimization_diagnostic_write_and_flush_failure_do_not_prevent_serve(self):
        core = SimpleNamespace(PROCESSFORGE_VERSION="test-core", resolve_workplace_root=Mock(return_value=Path("fixture")))
        args = argparse.Namespace(workplace="fixture", console=False, minimized=True)
        for operation in ("write", "flush"):
            for failure in (OSError, ValueError):
                with self.subTest(operation=operation, failure=failure.__name__):
                    stream = TTY()
                    with patch.object(sys, "stdout", stream), patch.object(service, "RuntimeProcess") as process:
                        def unavailable():
                            # Lose the output after the header, at the diagnostic.
                            stream_fault = patch.object(stream, operation, side_effect=failure("lost TTY"))
                            stream_fault.start()
                            self.addCleanup(stream_fault.stop)
                            return "unavailable"
                        with patch.object(console, "minimize_console", side_effect=unavailable) as minimize:
                            process.return_value.serve.return_value = 23
                            self.assertEqual(service.command_serve(args, core), 23)
                            process.return_value.serve.assert_called_once_with(0)
                            minimize.assert_called_once_with()

    def test_minimization_results_are_honest_and_startup_continues(self):
        for outcome in ("minimized", "unsupported", "not_owned", "unavailable", "failed", "unexpected"):
            with self.subTest(outcome=outcome), redirect_stdout(TTY()) as stream, patch.object(console, "minimize_console", return_value=outcome) as minimize:
                console.show_server_console("test", minimized=True)
                minimize.assert_called_once_with()
                self.assertEqual("Server startup continues" in stream.getvalue(), outcome != "minimized")
                self.assertEqual("Window remains visible" in stream.getvalue(), outcome != "minimized")

    def test_adapter_failure_does_not_stop_foreground_runtime_or_expose_exception(self):
        core = SimpleNamespace(PROCESSFORGE_VERSION="passed-core", resolve_workplace_root=Mock(return_value=Path("fixture")))
        args = argparse.Namespace(workplace="fixture", minimized=True, console=False)
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, "platform", "win32"), patch.object(windows_console, "minimize_console", side_effect=RuntimeError("PRIVATE_CANARY")), patch.object(service, "RuntimeProcess") as process, redirect_stdout(TTY()) as stream:
            process.return_value.serve.return_value = 23
            self.assertEqual(service.command_serve(args, core), 23)
            process.return_value.serve.assert_called_once_with(0)
            self.assertIn("Server startup continues", stream.getvalue())
            self.assertNotIn("PRIVATE_CANARY", stream.getvalue())

    def test_lazy_platform_dispatch_and_remote_refusals(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(windows_console, "minimize_console", return_value="not_owned") as windows, patch.object(linux_console, "minimize_console", return_value="unavailable") as linux:
            for platform, expected in (("win32", "not_owned"), ("linux", "unavailable"), ("darwin", "unsupported")):
                with self.subTest(platform=platform), patch.object(sys, "platform", platform):
                    self.assertEqual(console.minimize_console(), expected)
            windows.assert_called_once_with()
            linux.assert_called_once_with()
            windows.reset_mock()
            linux.reset_mock()
            for name in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY", "TMUX", "STY"):
                with self.subTest(environment=name), patch.dict(os.environ, {name: "present"}, clear=True):
                    self.assertEqual(console.minimize_console(), "unavailable")
            windows.assert_not_called()
            linux.assert_not_called()

    def test_minimized_and_console_parser_aliases(self):
        import processforge as core
        parser = core.build_parser()
        for command in ("runtime", "server"):
            for verb in ("serve", "run"):
                for options in ([], ["--minimized"], ["--console"], ["--console", "--minimized"]):
                    with self.subTest(command=command, verb=verb, options=options):
                        args = parser.parse_args([command, verb, "--workplace", "fixture with spaces", *options])
                        self.assertIs(args.func, core.command_runtime_serve)
                        self.assertEqual(args.minimized, "--minimized" in options)
                        self.assertEqual(args.console, "--console" in options)
        for verb in ("start", "status", "stop"):
            with self.subTest(verb=verb), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                parser.parse_args(["server", verb, "--workplace", "fixture", "--minimized"])
            self.assertEqual(error.exception.code, 2)


class WindowsChecks(unittest.TestCase):
    @contextmanager
    def desktop(self, *, clients=None, visible=True, window_class="ConsoleWindowClass"):
        kernel, user = Mock(), Mock()
        kernel.GetConsoleWindow.return_value = 42
        def process_list(buffer, size):
            pids = [os.getpid()] if clients is None else clients
            for index, pid in enumerate(pids[:size]):
                buffer[index] = pid
            return len(pids)
        def class_name(window, buffer, size):
            buffer.value = window_class
            return len(window_class)
        kernel.GetConsoleProcessList.side_effect = process_list
        user.IsWindowVisible.return_value = visible
        user.GetClassNameW.side_effect = class_name
        user.IsIconic.return_value = False
        user.ShowWindowAsync.return_value = True
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, "platform", "win32"), patch.object(sys, "stdout", TTY()), patch.object(windows_console, "_load_api", return_value=(kernel, user)), patch.object(windows_console.time, "sleep") as sleep:
            yield kernel, user, sleep

    def test_owned_classic_console_requires_observed_iconic_state(self):
        with self.desktop() as (kernel, user, sleep):
            user.IsIconic.side_effect = [False, False, True]
            self.assertEqual(windows_console.minimize_console(), "minimized")
            user.ShowWindowAsync.assert_called_once_with(42, 6)
            self.assertGreaterEqual(kernel.GetConsoleProcessList.call_count, 3)
            sleep.assert_called_once_with(0.05)

    def test_already_minimized_console_does_not_send_another_request(self):
        with self.desktop() as (_, user, _):
            user.IsIconic.return_value = True
            self.assertEqual(windows_console.minimize_console(), "minimized")
            user.ShowWindowAsync.assert_not_called()

    def test_shared_foreign_empty_and_oversized_client_lists_are_refused(self):
        for pids, expected in (([os.getpid(), os.getpid() + 1], "not_owned"), ([os.getpid() + 1], "not_owned"), ([], "unavailable"), ([1, 2, 3], "not_owned")):
            with self.subTest(pids=pids), self.desktop(clients=pids) as (_, user, _):
                self.assertEqual(windows_console.minimize_console(), expected)
                user.ShowWindowAsync.assert_not_called()

    def test_conpty_and_nonclassic_windows_are_never_minimized(self):
        for visible, class_name, expected in ((False, "ConsoleWindowClass", "unavailable"), (True, "CASCADIA_HOSTING_WINDOW_CLASS", "unsupported"), (True, "", "unavailable")):
            with self.subTest(visible=visible, window_class=class_name), self.desktop(visible=visible, window_class=class_name) as (_, user, _):
                self.assertEqual(windows_console.minimize_console(), expected)
                user.ShowWindowAsync.assert_not_called()

    def test_queued_request_without_confirmation_and_native_errors_fail_closed(self):
        for mode in ("no_confirmation", "request_refused", "native_error"):
            with self.subTest(mode=mode), self.desktop() as (_, user, sleep):
                if mode == "request_refused":
                    user.ShowWindowAsync.return_value = False
                elif mode == "native_error":
                    user.ShowWindowAsync.side_effect = OSError("fixture")
                self.assertEqual(windows_console.minimize_console(), "failed")
                self.assertLessEqual(sleep.call_count, 5)
                if mode == "no_confirmation":
                    self.assertEqual(sleep.call_count, 5)

    def test_changed_window_or_new_console_client_revokes_ownership(self):
        for mode in ("window", "client"):
            with self.subTest(mode=mode), self.desktop() as (kernel, user, _):
                if mode == "window":
                    kernel.GetConsoleWindow.side_effect = [42, 99]
                else:
                    def attach_other(window, command):
                        kernel.GetConsoleProcessList.side_effect = lambda buffer, size: 2
                        return True
                    user.ShowWindowAsync.side_effect = attach_other
                self.assertEqual(windows_console.minimize_console(), "not_owned")
                if mode == "window":
                    user.ShowWindowAsync.assert_not_called()

    def test_environment_and_stream_refusals_happen_before_native_binding(self):
        cases = [({"WT_SESSION": "present"}, TTY(), "unsupported"),
                 ({"WT_PROFILE_ID": "present"}, TTY(), "unsupported")]
        cases += [({name: "present"}, TTY(), "unavailable") for name in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY", "TMUX", "STY")]
        cases += [({}, stream, "unavailable") for stream in (None, io.StringIO(), SimpleNamespace(isatty=Mock(side_effect=ValueError)))]
        for env, stream, expected in cases:
            with self.subTest(env=env, stream=type(stream).__name__), patch.dict(os.environ, env, clear=True), patch.object(sys, "platform", "win32"), patch.object(sys, "stdout", stream), patch.object(windows_console, "_load_api") as load:
                self.assertEqual(windows_console.minimize_console(), expected)
                load.assert_not_called()
        with patch.object(sys, "platform", "linux"), patch.object(windows_console, "_load_api") as load:
            self.assertEqual(windows_console.minimize_console(), "unsupported")
            load.assert_not_called()

    def test_no_console_or_missing_native_api_is_unavailable(self):
        with self.desktop() as (kernel, user, _):
            kernel.GetConsoleWindow.return_value = 0
            self.assertEqual(windows_console.minimize_console(), "unavailable")
            user.ShowWindowAsync.assert_not_called()
        with self.desktop(), patch.object(windows_console, "_load_api", side_effect=OSError):
            self.assertEqual(windows_console.minimize_console(), "unavailable")


class LinuxChecks(unittest.TestCase):
    terminal = linux_console._Terminal(42, 111, 222, 333, 34817)
    normal = '_NET_WM_PID(CARDINAL) = 222\nWM_CLASS(STRING) = "xterm", "XTerm"\nWM_STATE(WM_STATE):\n\t\twindow state: Normal\n_NET_WM_STATE(ATOM) = \n'
    iconic = normal.replace("state: Normal", "state: Iconic").replace("(ATOM) = \n", "(ATOM) = _NET_WM_STATE_HIDDEN\n")

    @contextmanager
    def desktop(self, *, properties=None):
        outputs = iter(properties if properties is not None else [self.normal, self.iconic])
        def run(argv, **kwargs):
            output = next(outputs) if argv[0] == "xprop" else ""
            return subprocess.CompletedProcess(argv, 0, stdout=output)
        with patch.dict(os.environ, {"DISPLAY": ":0", "WINDOWID": "0x2a", "XDG_SESSION_TYPE": "x11"}, clear=True), patch.object(sys, "platform", "linux"), patch.object(sys, "stdout", TTY()), patch.object(sys, "stdin", TTY()), patch.object(linux_console, "_owned_terminal", return_value=self.terminal) as owned, patch.object(linux_console.shutil, "which", side_effect=lambda name: name), patch.object(linux_console.subprocess, "run", side_effect=run) as command, patch.object(linux_console.time, "sleep") as sleep:
            yield owned, command, sleep

    def assert_no_minimize(self, command):
        self.assertFalse(any(call.args[0][0] == "xdotool" for call in command.call_args_list))

    def test_owned_x11_requires_both_iconic_and_hidden_confirmation(self):
        with self.desktop() as (owned, command, _):
            self.assertEqual(linux_console.minimize_console(), "minimized")
            argv = [call.args[0] for call in command.call_args_list]
            self.assertEqual(argv[1], ["xdotool", "windowminimize", "42"])
            self.assertEqual(owned.call_count, 3)
            for call in command.call_args_list:
                self.assertIs(call.kwargs["shell"], False)
                self.assertEqual(call.kwargs["timeout"], 1.0)
                self.assertEqual(call.kwargs["stdin"], subprocess.DEVNULL)

    def test_wayland_xwayland_ssh_multiplexer_and_headless_refuse_before_gui(self):
        cases = [({"WAYLAND_DISPLAY": "wayland-0"}, "unsupported"),
                 ({"XDG_SESSION_TYPE": "wayland"}, "unsupported"),
                 ({"DISPLAY": ""}, "unavailable"), ({"DISPLAY": "localhost:10.0"}, "unavailable"),
                 ({"DISPLAY": "remote:0"}, "unavailable"), ({"TERM": "screen-256color"}, "unavailable"),
                 ({"TERM": "tmux-256color"}, "unavailable")]
        cases += [({name: "present"}, "unavailable") for name in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY", "TMUX", "STY", "ZELLIJ", "ZELLIJ_SESSION_NAME")]
        for env, expected in cases:
            with self.subTest(env=env), self.desktop() as (owned, command, _), patch.dict(os.environ, env):
                self.assertEqual(linux_console.minimize_console(), expected)
                owned.assert_not_called()
                command.assert_not_called()

    def test_bad_window_ids_and_missing_streams_are_refused_before_gui(self):
        for value in ("", "0", "-1", "0x100000000", "1;bad", "42\n", "4294967296"):
            with self.subTest(window_id=value), self.desktop() as (owned, command, _), patch.dict(os.environ, {"WINDOWID": value}):
                self.assertEqual(linux_console.minimize_console(), "not_owned")
                owned.assert_not_called()
                command.assert_not_called()
        for name in ("stdin", "stdout"):
            for stream in (None, io.StringIO(), SimpleNamespace(isatty=Mock(side_effect=OSError))):
                with self.subTest(stream=name, value=type(stream).__name__), self.desktop() as (_, command, _), patch.object(sys, name, stream):
                    self.assertEqual(linux_console.minimize_console(), "unavailable")
                    command.assert_not_called()

    def test_ambiguous_terminal_missing_tools_or_inaccessible_proc_never_targets_a_window(self):
        for mode, expected in (("not_owned", "not_owned"), ("missing_tool", "unavailable"), ("permission", "unavailable")):
            with self.subTest(mode=mode), self.desktop() as (owned, command, _):
                if mode == "not_owned":
                    owned.return_value = None
                elif mode == "permission":
                    owned.side_effect = PermissionError
                else:
                    with patch.object(linux_console.shutil, "which", return_value=None):
                        self.assertEqual(linux_console.minimize_console(), expected)
                    command.assert_not_called()
                    continue
                self.assertEqual(linux_console.minimize_console(), expected)
                command.assert_not_called()

    def test_wrong_window_pid_class_and_unmanaged_state_are_refused(self):
        cases = [(self.normal.replace("= 222", "= 999"), "not_owned"),
                 (self.normal.replace('"XTerm"', '"Other"'), "not_owned"),
                 (self.normal.replace("state: Normal", "state: Withdrawn"), "unavailable")]
        for properties, expected in cases:
            with self.subTest(properties=properties), self.desktop(properties=[properties]) as (_, command, _):
                self.assertEqual(linux_console.minimize_console(), expected)
                self.assert_no_minimize(command)

    def test_x11_request_without_full_confirmation_is_failed_with_bounded_polling(self):
        partials = [self.normal, self.iconic.replace("_NET_WM_STATE_HIDDEN", ""), self.iconic.replace("state: Iconic", "state: Normal")]
        for partial in partials:
            with self.subTest(properties=partial), self.desktop(properties=[self.normal] + [partial] * 4) as (_, command, sleep):
                self.assertEqual(linux_console.minimize_console(), "failed")
                self.assertEqual(command.call_count, 6)
                self.assertEqual(sleep.call_count, 3)

    def test_changed_ownership_is_rechecked_before_and_after_request(self):
        for stage in ("before", "after"):
            with self.subTest(stage=stage), self.desktop() as (owned, command, _):
                owned.side_effect = [self.terminal, None] if stage == "before" else [self.terminal, self.terminal, None]
                self.assertEqual(linux_console.minimize_console(), "not_owned")
                if stage == "before":
                    self.assert_no_minimize(command)

    def test_already_iconic_window_needs_no_new_request(self):
        with self.desktop(properties=[self.iconic]) as (_, command, _):
            self.assertEqual(linux_console.minimize_console(), "minimized")
            self.assert_no_minimize(command)

    def test_subprocess_timeout_or_command_failure_is_not_success(self):
        with self.desktop() as (_, command, _):
            command.side_effect = subprocess.TimeoutExpired("xprop", 1)
            self.assertEqual(linux_console.minimize_console(), "failed")
        for failure in ("query", "request", "confirmation"):
            with self.subTest(failure=failure), self.desktop() as (_, command, _):
                def run(argv, **kwargs):
                    failed = (failure == "query" and command.call_count == 1) or (failure == "request" and argv[0] == "xdotool") or (failure == "confirmation" and command.call_count == 3)
                    return subprocess.CompletedProcess(argv, 1 if failed else 0, stdout=self.normal)
                command.side_effect = run
                self.assertEqual(linux_console.minimize_console(), "unavailable" if failure == "query" else "failed")
                if failure == "query":
                    self.assert_no_minimize(command)

    @contextmanager
    def ownership(self, **changes):
        data = dict(device=34817, output_device=34817, uid=1000, euid=1000, parent_uid=1000,
                    sid=111, group=111, foreground=111, exe="xterm", same_executable=True,
                    cmdline=b"xterm\0-e\0python\0app.py\0", children="111", parent_after=222,
                    parent_start_after=333, exclusive=True)
        data.update(changes)
        class ProcPath:
            def __init__(self, value): self.value = str(value)
            def __truediv__(self, child): return ProcPath(self.value + "/" + str(child))
            def stat(self): return SimpleNamespace(st_uid=data["parent_uid"])
            def resolve(self, strict=False): return SimpleNamespace(name=data["exe"])
            def read_bytes(self): return data["cmdline"]
            def read_text(self, **kwargs): return data["children"]
            def samefile(self, other): return data["same_executable"]
        with ExitStack() as stack:
            stack.enter_context(patch.object(linux_console, "Path", ProcPath))
            stack.enter_context(patch.object(sys, "stdin", SimpleNamespace(isatty=lambda: True, fileno=lambda: 0)))
            stack.enter_context(patch.object(sys, "stdout", SimpleNamespace(isatty=lambda: True, fileno=lambda: 1)))
            stack.enter_context(patch.object(linux_console.os, "fstat", side_effect=lambda fd: SimpleNamespace(st_mode=stat.S_IFCHR, st_rdev=data["device"] if fd == 0 else data["output_device"])))
            for name, value in (("getpid", 111), ("getuid", data["uid"]), ("geteuid", data["euid"]), ("getsid", data["sid"]), ("getpgrp", data["group"]), ("tcgetpgrp", data["foreground"])):
                stack.enter_context(patch.object(linux_console.os, name, return_value=value, create=True))
            stack.enter_context(patch.object(linux_console.os, "getppid", side_effect=[222, data["parent_after"]]))
            stack.enter_context(patch.object(linux_console.shutil, "which", return_value="/python"))
            stack.enter_context(patch.object(linux_console, "_process_stat", side_effect=[(222, 1), (1, 333), (1, data["parent_start_after"])]))
            stack.enter_context(patch.object(linux_console, "_exclusive_terminal", return_value=data["exclusive"]))
            yield

    def test_direct_exclusive_xterm_parent_is_required(self):
        with self.ownership():
            self.assertEqual(linux_console._owned_terminal(42), self.terminal)
        refusals = [dict(output_device=34818), dict(uid=1001), dict(parent_uid=1001),
                    dict(sid=110), dict(group=110), dict(foreground=110), dict(exe="bash"),
                    dict(same_executable=False), dict(cmdline=b"xterm\0-e\0"),
                    dict(cmdline=b"xterm\0-into\0" + b"123\0-e\0python\0"),
                    dict(cmdline=b"xterm\0-Sfixture\0-e\0python\0"),
                    dict(cmdline=b"xterm\0python\0"), dict(children="111 112"),
                    dict(exclusive=False), dict(parent_after=999), dict(parent_start_after=334)]
        for changes in refusals:
            with self.subTest(changes=changes), self.ownership(**changes):
                self.assertIsNone(linux_console._owned_terminal(42))

    def test_proc_scan_refuses_other_session_or_tty_users_and_limits(self):
        # /proc fields start at state: ppid, pgrp, session, tty_nr follow it.
        own = ["S", "222", "111", "111", "34817"]
        other = ["S", "1", "112", "112", "34818"]
        for mode, expected in (("exclusive", True), ("session", False), ("tty", False), ("limit", False), ("vanished", True)):
            with self.subTest(mode=mode), ExitStack() as stack:
                fields = list(other)
                if mode == "session": fields[3] = "111"
                if mode == "tty": fields[4] = "34817"
                def process_fields(pid):
                    if pid == 111: return own
                    if mode == "vanished": raise FileNotFoundError
                    return fields
                stack.enter_context(patch.object(linux_console, "_process_fields", side_effect=process_fields))
                stack.enter_context(patch.object(linux_console.os, "major", return_value=136, create=True))
                stack.enter_context(patch.object(linux_console.os, "minor", return_value=1, create=True))
                scan = stack.enter_context(patch.object(linux_console.os, "scandir"))
                scan.return_value.__enter__.return_value = iter([SimpleNamespace(name="112")])
                if mode == "limit": stack.enter_context(patch.object(linux_console, "_PROCESS_SCAN_LIMIT", 0))
                self.assertEqual(linux_console._exclusive_terminal(111, 34817), expected)

    def test_proc_scan_cannot_prove_ownership_on_permission_error_or_deadline(self):
        own = ["S", "222", "111", "111", "34817"]
        with patch.object(linux_console, "_process_fields", side_effect=[own, PermissionError()]), patch.object(linux_console.os, "major", return_value=136, create=True), patch.object(linux_console.os, "minor", return_value=1, create=True), patch.object(linux_console.os, "scandir") as scan:
            scan.return_value.__enter__.return_value = iter([SimpleNamespace(name="112")])
            with self.assertRaises(PermissionError):
                linux_console._exclusive_terminal(111, 34817)
        with patch.object(linux_console, "_process_fields", return_value=own), patch.object(linux_console.os, "major", return_value=136, create=True), patch.object(linux_console.os, "minor", return_value=1, create=True), patch.object(linux_console.os, "scandir") as scan, patch.object(linux_console.time, "monotonic", side_effect=[0, 1]):
            scan.return_value.__enter__.return_value = iter([SimpleNamespace(name="112")])
            self.assertFalse(linux_console._exclusive_terminal(111, 34817))


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if result.wasSuccessful():
        print(f"PASS: {result.testsRun} server-console checks (desktop APIs mocked; native GUI acceptance excluded).")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
