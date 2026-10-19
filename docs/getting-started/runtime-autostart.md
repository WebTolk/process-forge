# Runtime Autostart And Codex MCP Startup

ProcessForge has two different startup models:

- **PF App Server (PF Runtime)** is a workplace-scoped loopback HTTP service.
  It can run as a foreground process, as an explicitly detached background
  process, or on Windows as an opt-in per-user scheduled task.
- **PF MCP** is a stdio server for Codex. Codex owns this process and starts it
  from Codex MCP configuration when a host session needs the server.

Garage does not require PF Runtime. Install Runtime autostart only for a Forge
workplace whose coordination model requires the long-lived service. On Linux,
Runtime may be started manually or by operator-managed background tooling;
managed `systemd --user` installation is not provided by the current CLI.
The autostart backend reports `unsupported` outside Windows.

Do not register `tools/pf_runtime/mcp_server.py` with Windows autostart. A
detached stdio MCP process has no connected MCP client and cannot serve useful
JSON-RPC traffic.

These are operator setup and maintenance commands. An ordinary project agent
must not install, start, restart or repair Runtime, MCP or hooks. Use the same
Python environment as in [installation](installation.md), and budget optional
processes separately as described in [requirements](../requirements.md).

## Manual Runtime Lifecycle

From the installed ProcessForge distribution root:

```bash
python bin/pf.py runtime start --workplace <workplace>
python bin/pf.py runtime status --workplace <workplace>
python bin/pf.py runtime doctor --workplace <workplace>
python bin/pf.py runtime stop --workplace <workplace>
```

`runtime start` launches `runtime serve` in a detached background process. The
service writes singleton state under `<workplace>/runtime/pf-runtime/`, binds a
loopback HTTP endpoint on `127.0.0.1`, and protects requests with a local bearer
token.

## Foreground server window

To run the server in the current terminal, use the operator launcher:

```bash
python bin/pf-server.py run --workplace <workplace>
```

On a TTY, foreground `run`/`serve` automatically shows the PF logo, the running
Core version, PID and the purpose of the process. `--console` remains accepted
but is no longer required for this header. The header appears before binding
the endpoint; check `runtime status` or `runtime doctor` for readiness. Closing
this server window stops the foreground server.

To request minimization of a dedicated server window, add `--minimized`:

```bash
python tools/processforge.py server run --workplace <workplace> --minimized
```

`python bin/pf.py server run ...`, `server serve ...`, `runtime run ...` and
`runtime serve ...` use the same foreground policy. Without `--minimized`, PF
does not minimize the terminal in which you enter the command. The flag does
not create a separate terminal or detach the process; the operator must supply
a dedicated window whose ownership PF can verify.

| Environment | Minimization boundary |
| --- | --- |
| Windows classic console | Only a visible, dedicated console with the current server as its sole console client. Shared consoles are refused. |
| Windows Terminal / ConPTY | Unsupported; PF does not minimize a host window containing other tabs. |
| Linux X11 | Only the narrow dedicated `xterm -e` backend on a local display, with window ID, window PID and parent-process ownership checks. Other terminal emulators are unsupported. |
| Wayland / XWayland | Unsupported. Configure terminal/desktop launch behavior separately if needed. |

On Windows, `bin/pf.py` and `bin/pf-server.py` keep an extra Python launcher
attached to the console, so the sole-client check refuses minimization. For a
dedicated window, its launcher must execute
`python tools/processforge.py server run --workplace <workplace> --minimized`
directly, without another attached shell or launcher process. A new shell tab
alone does not establish ownership. The scheduled action below uses this direct
entrypoint.

On Linux, the X11 backend needs preinstalled `xprop` and `xdotool`; PF does not
install them. Launch Python directly under `xterm -e`, without an intermediate
shell, for example:

```bash
xterm -e python tools/processforge.py server run --workplace "../pf-workplace" --minimized
```

PF verifies the parent terminal, `WINDOWID` and `_NET_WM_PID` before sending a
request, then checks the minimized window state. Remote displays and ambiguous
ownership are refused. Missing helpers leave minimization unavailable.

Without a TTY, including redirected or missing standard output, PF emits no
server header and performs no window actions. SSH, headless and `tmux`/`screen`
sessions do not receive minimization attempts. On a TTY, an unsupported backend,
unproven ownership or unconfirmed minimization produces a diagnostic and server
startup continues. A minimization request is not proof that the desktop minimized
the window.

Use console Python (`python.exe` on Windows) for a visible server window.
`pythonw.exe` is windowless, not minimized; its standard streams may be `None`.
Likewise, detached `runtime start` is a background launch, not a minimized window.

The existing [read-only monitor](../concepts/runtime-monitor.md) runs separately;
neither foreground launch nor `--minimized` opens it. Closing the monitor leaves
the server running. A Textual monitor and the proposed
`autostart_pf_app_server_monitor` configuration field are future work and are
not available in the current CLI or configuration.

## Windows Runtime Autostart

Windows autostart is opt-in and uses Task Scheduler. The scheduled action runs
the configured Python directly with `tools/processforge.py runtime serve --minimized`
in the foreground, so Task Scheduler owns the process lifecycle.
It uses the current interactive user, least privilege, a logon trigger, bounded
restart-on-failure settings, and a deterministic task name derived from the
workplace path.

The generated profile requests minimization of the server's own dedicated
console using the same checks above. It does not launch the monitor or switch
to a detached wrapper. Task Scheduler's `Hidden` setting controls task visibility;
it does not minimize the console. An explicit `--python` executable is preserved;
choosing `pythonw.exe` gives a windowless process, not a minimized console.

Inspect the task:

```powershell
python bin/pf.py runtime autostart status --workplace <workplace>
```

Plan or install it:

```powershell
python bin/pf.py runtime autostart install --workplace <workplace>
python bin/pf.py runtime autostart install --workplace <workplace> --apply
```

Plan or remove it:

```powershell
python bin/pf.py runtime autostart remove --workplace <workplace>
python bin/pf.py runtime autostart remove --workplace <workplace> --apply
```

If status reports drift, use `--replace` on install to overwrite the deterministic
ProcessForge task definition. Use `--force` on remove only when you intentionally
want to remove a drifted task with the deterministic ProcessForge task name.

Older profiles used `bin/pf.py` without `--minimized`; after a Core update their
action intentionally reports drift. Updating files does not rewrite the
registered task. An operator can review and apply the replacement explicitly:

```powershell
python bin/pf.py runtime autostart install --workplace <workplace> --replace
python bin/pf.py runtime autostart install --workplace <workplace> --replace --apply
```

Optional task action settings:

```powershell
python bin/pf.py runtime autostart install --workplace <workplace> --distribution-root <processforge-install> --python <python> --port 0 --interval 2.0 --delay-seconds 10 --apply
```

After installation, verify with:

```powershell
python bin/pf.py runtime autostart status --workplace <workplace>
python bin/pf.py runtime status --workplace <workplace>
python bin/pf.py runtime doctor --workplace <workplace>
```

Moving Python, its virtual environment or the ProcessForge installation changes
the scheduled command and requires reinstalling the task. Shell activation is
not inherited by Task Scheduler; the configured interpreter must have PyYAML.

## Codex MCP Registration

Codex MCP registration is separate from Runtime autostart. ProcessForge manages
Codex host configuration only when explicitly requested:

```powershell
python bin/pf.py codex-mcp status --workplace <workplace>
python bin/pf.py codex-mcp install --workplace <workplace>
python bin/pf.py codex-mcp install --workplace <workplace> --apply
python bin/pf.py codex-mcp remove --workplace <workplace>
python bin/pf.py codex-mcp remove --workplace <workplace> --apply
```

The default server name is `processforge`. Use `--name`, `--python`, `--codex`,
or `--distribution-root` when the host needs a non-default executable or
installation path. An explicit `--python` value is an exact executable pin;
`status` reports drift when the stored command differs. Use `--replace` to replace a drifted Codex registration and
`--force` to remove a drifted registration by name.

Codex must be restarted or reloaded after a registration change. Each fresh host
session starts its own connected Python stdio MCP process. The MCP registration
does not create a Windows service, scheduled task, idle daemon, or always-on
network endpoint.
