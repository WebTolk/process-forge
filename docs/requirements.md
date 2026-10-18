# Requirements

Use this checklist before [installation](getting-started/installation.md).
ProcessForge runs as a local Python CLI. Garage work does not require PF
Runtime, MCP, Codex hooks, or a manually opened Agent Ledger session.

## Python and libraries

Python **3.11+ is recommended**. Current acceptance evidence uses CPython
**3.14.3 on Windows**; it does not certify every Python version or operating
system combination. Parsing the source with an older Python grammar is not a
substitute for running the relevant tests on that interpreter.

| Component | Requirement and purpose |
| --- | --- |
| PyYAML | `PyYAML>=6.0`, the only external Python dependency in `requirements.txt`; reads and writes YAML configuration and artifacts. |
| `sqlite3` | A working standard-library module and SQLite build with UPSERT support. Local event and raw-hook journals use transactions, WAL and `synchronous=FULL`. No separate database server is needed. |
| SQLite FTS5 | Required for indexed full-text resource search. PF probes this capability; unavailable FTS5 is reported as `degraded` / `fts5_unavailable`. A working journal does not prove FTS5 is available. |
| `ssl` and CA trust | Required for HTTPS downloads and HTTPS egress. Python must provide SSL support and trust the destination's certificate chain. Windows egress uses operating system certificate stores. |
| `zlib` and `zipfile` | Needed to read compressed release/update archives and create DEFLATE ZIP packages. A reduced Python build without `zlib` is insufficient for these operations. |
| `venv` and `pip` | Used to create an isolated environment and install PyYAML. Some OS distributions package these separately; provision them before setup. They are setup tools, not background services. |
| Windows `ctypes` | Required by Windows file-security preservation, process diagnostics and native egress support. Use Python with working Windows standard-library bindings. |

The CLI and MCP/HTTP services use Python's standard library; an external MCP
SDK, web framework, Node.js, PHP or PowerShell is not a general CLI dependency.

## Storage and permissions

Keep three locations separate: the replaceable ProcessForge distribution, the
mutable workplace, and each project. Use a UTF-8 capable environment. The account
running PF needs to read the distribution and selected resources, and to create,
write, rename and lock files in the workplace and project `.pf/` directories.
Updating Core additionally needs write access to the distribution and space for
the archive, staged files and backups. Validation can also write reports.

Store SQLite journals on a local filesystem with reliable locking and support
for adjacent `-wal` and `-shm` files. Write permission on the database alone is
insufficient; its directory must also be writable. Do not assume a network share
or synchronised folder provides the same locking guarantees. Allow space for
journals, indexes, artifacts and retained backups according to the workload;
there is no single measured disk minimum.

Keep task scratch in `.pf/tmp/`, with durable evidence in `.pf/artifacts/`.
See [temporary files and old-file notifications](temporary-files.md).

## Memory planning

Start by reserving **512 MiB per app-server process**; **1 GiB is a recommended
initial reserve for a small workplace**. These are planning estimates, **not a
certified minimum or an enforced cap**. A limited Windows observation of two
existing processes found roughly 115–136 MiB working sets, 136–169 MiB private
commit and a 182 MiB lifetime working-set peak. It was not a constrained-memory
or maximum-load test.

Measure your own workload, especially with large YAML inventories, indexes or
many concurrent requests. Budget the OS, IDE, AI host, workers, optional Runtime,
MCP processes and other applications separately. Multiple app-servers each need
their own reserve; the CLI does not need an app-server for ordinary file-only work.

## Read-only preflight

Run these with the Python interpreter chosen for PF, after installing its
dependencies. They print versions and exercise an in-memory database; they do
not create a workplace, project, journal or service:

```bash
python --version
python -m pip show PyYAML
python -c "import sqlite3, ssl, zlib, venv, yaml; print('PyYAML', yaml.__version__); print('SQLite', sqlite3.sqlite_version); print('SSL', ssl.OPENSSL_VERSION); print('zlib', zlib.ZLIB_VERSION)"
python -c "import sqlite3; db = sqlite3.connect(':memory:'); db.execute('CREATE TABLE probe (id INTEGER PRIMARY KEY, value TEXT)'); db.execute('INSERT INTO probe VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET value=excluded.value', ('ok',)); db.execute('CREATE VIRTUAL TABLE search_probe USING fts5(content)'); db.close(); print('UPSERT and FTS5 available')"
python bin/pf.py version
python bin/pf.py --help
```

On Windows also check `python -c "import ctypes; print('ctypes available')"`.
An in-memory check cannot validate on-disk WAL, directory permissions, remote
certificate trust, or the full PF test suite. Do not disable certificate
verification to make a failed HTTPS check pass.

## Optional tools and services

Git is used for a source clone and development/release checks; an extracted
release can run without Git unless a selected integration needs it. A worker's
configured AI CLI, shell, tools and credentials are needed only for that driver
or selected process. Pack/platform requirements can add their own dependencies.

PF Runtime and host-owned stdio MCP are separate opt-in components. Windows
Runtime autostart uses Task Scheduler (`schtasks.exe`); it is not a cross-platform
service installer. See [Runtime and MCP startup](getting-started/runtime-autostart.md).
Ordinary project agents must not install or repair this infrastructure.

Source references: [Python dependencies](../requirements.txt),
[SQLite journal storage](../src/processforge_core/sqlite_storage.py),
[FTS5 capability and indexing](../src/processforge_core/resources/local_search.py),
[HTTPS egress](../src/processforge_core/egress/transport.py),
[Windows file security](../src/processforge_platforms/windows_file_security.py),
[ZIP packaging](../tools/processforge.py),
[Core update archives](../src/processforge_core/maintenance/update.py), and
[Windows autostart](../tools/pf_runtime/windows_autostart.py).
