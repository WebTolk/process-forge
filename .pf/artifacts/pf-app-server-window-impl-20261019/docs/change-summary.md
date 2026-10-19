# PF App Server window: EN/RU documentation summary

Status: ready_for_review.
Owner: pf-app-server-window-docs; attempt 2.

## Changes

The six owned documents now describe automatic foreground TTY PF logo, running
Core version and PID; the header precedes readiness and does not prove it.
The historical --console flag remains accepted. --minimized is an explicit
request for a dedicated owned window, not a request to create a terminal,
detach the process or open the monitor.

Both locales document classic visible Windows consoles with a sole current-PID
client; Windows Terminal/ConPTY and shared console refusal; direct Scheduler
execution of tools/processforge.py runtime serve --minimized with the exact
configured interpreter; bin launcher/attached shell ownership limits; task
Hidden versus window minimization; and intentional old task action drift with
operator-only --replace preview/apply migration.

The Linux section documents direct xterm -e Python on a local X11 display,
preinstalled xprop/xdotool, parent/window identity checks and state confirmation.
Other terminals, remote displays, Wayland/XWayland, SSH, multiplexers and
headless window actions are excluded. Non-TTY or missing stdout suppresses the
header and GUI work. pythonw is windowless; runtime start remains detached.

After primary's DOCS_REFINEMENT, the lead --minimized example uses the direct
tools/processforge.py server run entrypoint in both locales; the ordinary
bin/pf-server.py example is reserved for a current-terminal launch. Newly added
Russian prose uses natural Russian; the RU server-window section and all owned
links to it now use the heading/anchor Окно сервера / окно-сервера.

The existing read-only monitor remains separate. Textual and
autostart_pf_app_server_monitor are explicitly future work and appear in no
executable setup example.

## Verification

- Source parity checked using Serena: console.show_server_console and
  minimize_console, service.command_serve, RuntimeCommandParser aliases/flags,
  bin/pf.py exec_processforge, windows_autostart.runtime_action, Windows
  ownership/minimization functions and Linux ownership/minimization functions.
- CLI --help passed for bin/pf-server.py run; bin/pf.py runtime serve,
  server serve and runtime run; tools/processforge.py server run and runtime
  serve; and runtime autostart install. --minimized, --console, --replace and
  --apply match the documentation. No command started a server or changed a task.
- All six Markdown files decoded as UTF-8, had balanced fenced code blocks,
  and passed checks for 30 relative links and heading anchors.
- Scoped git diff --check passed; no pre-existing modifications were present
  in the six owned documentation files before this worker's edits.
- Authorized PF Python guidance was used from the immutable inline design
  excerpt. No external knowledge bodies were opened.

## Coordination and remaining acceptance

Own Agent Ledger check-in and heartbeat succeeded. Shared PF chat received
READ_ACK for the original scope and for the Windows direct-entrypoint/Linux
backend clarification. The assigned report is returned for PF capture.

This worker did not run native desktop minimization, Runtime lifecycle,
scheduled-task mutation or Linux GUI acceptance. Actual platform observation,
assurance, independent review, integration and task commit remain with primary
and the designated workers. No subagents or scratch files were created.
