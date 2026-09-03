# Runtime Autostart And Codex MCP Startup

ProcessForge has two different startup models:

- **PF Runtime** is a workplace-scoped loopback HTTP service. It can run as a
  foreground process, as an explicitly detached background process, or on
  Windows as an opt-in per-user scheduled task.
- **PF MCP** is a stdio server for Codex. Codex owns this process and starts it
  from Codex MCP configuration when a host session needs the server.

Garage does not require PF Runtime. Install Runtime autostart only for a Forge
workplace whose coordination model requires the long-lived service. On Linux,
Runtime may be started manually or by operator-managed background tooling;
managed `systemd --user` installation is not provided in 1.1.0.

Do not register `tools/pf_runtime/mcp_server.py` with Windows autostart. A
detached stdio MCP process has no connected MCP client and cannot serve useful
JSON-RPC traffic.

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

## Windows Runtime Autostart

Windows autostart is opt-in and uses Task Scheduler. The scheduled action runs
`runtime serve` in the foreground so Task Scheduler owns the process lifecycle.
It uses the current interactive user, least privilege, a logon trigger, bounded
restart-on-failure settings, and a deterministic task name derived from the
workplace path.

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

Moving Python or the ProcessForge installation changes the scheduled command and
requires reinstalling the task.

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
