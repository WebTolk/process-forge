# Alpha3 maintenance code quality before independent review

Registered tools: Python3.14.3, pytest9.1.1, Ruff0.17.1, mypy2.4.0,
coverage7.16.2, Bandit1.9.4; SQLite3.50.4. No product dependency was added.

Ruff lint passed for all owned production/test modules and both adapted scripts;
the subsequently added junction test passed its own lint check. Ruff format
passed all 17 Python files. Strict mypy passed the seven new/extracted production
modules with --follow-imports=silent --ignore-missing-imports --strict. Bandit
passed six operation/adapter files: 1842 lines, zero findings and zero nosec skips.

Explicit narrow compatibility boundaries: two standalone scripts must establish
source package paths before Core imports and document their E402 exemption.
One no-untyped-call waiver is restricted to the existing RawHookJournal._accept
batch admission; the existing owner is outside this feature's typing scope. No
global type/lint disabling or universal Any-core dependency was introduced.

Actually used PF knowledge includes the frozen Python typing/Protocol,
dataclasses, pathlib, PEP8/257 excerpts and the selected current architecture/OOP
clarification/migration rules. Applied patterns are existing repositories, an
ordered application service, narrow operation ports, CLI/legacy adapters and
immutable file/digest receipts. Constructors remain cold; Core imports and
construction passed without Main or Host services.

Native reports and capsules stay immutable. Primary QA changes were sequential
after each native attempt completed: formatting, explicit JSON field typing,
the legacy call boundary, source script bootstrapping and standalone test package
setup/staticmethod fault injection. Initial failures and later passing evidence
are retained; no initial failing result is presented as a pass.

No dependency audit of the external QA environment was used as product proof.
No device update, Runtime/MCP restart or connected-host alpha3 claim is included.
Release/archive qualification and independent review remain separate gates.
