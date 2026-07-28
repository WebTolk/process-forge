# Handoff contracts

Handoff package хранится в `.pf/handoffs/<handoff-id>/`.

В пакет входят `handoff.yaml`, `handoff.md`, `input-manifest.yaml`, `expected-output.yaml` и `return-package.yaml`. Команда `handoff-status` показывает `waiting_for_agent`, `ready`, `accepted`, `returned`, `finalized` или `needs_operator`.

`handoff-return` принимает конкретные returned artifacts. ProcessForge не считает handoff завершённым без ожидаемых файлов и return package.

Handoff state координирует Agent Director, а не Process Execution Inspector.
Inspector может сообщить, создала ли назначенная worker task runtime proof и
required outputs; он не принимает, не возвращает, не финализирует и не
маршрутизирует handoffs. См.
[Граница Director, Ledger, Inspector и Worker](director-ledger-inspector-boundary.md).
