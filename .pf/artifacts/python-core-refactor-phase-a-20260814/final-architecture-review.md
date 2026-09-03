# Final Architecture Review

## Вердикт

**pass_with_conditions**

Phase A-артефакты в целом закрывают цель задания: пять условий независимого review превращены в явные deliverables/gates, unsupported claim о уже завершённой реализации не найден, а первый slice описан как `behavior-preserving`, общий для CLI и Runtime/MCP и привязанный к package/import stabilization. Но перед Phase B/C нужно устранить одно межартефактное напряжение: target architecture всё ещё формулирует перевод runtime/MCP на package imports как отдельный Phase 3 шаг, тогда как план уже требует общий Process Definition API для CLI и Runtime/MCP в gate Phase C.

## Что подтверждено

- Пять обязательных условий из независимого review перенесены в план буквально и без потерь: `.pf/artifacts/python-core-refactor-phase-a-20260814/independent-architecture-review.md:118-124` -> `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-refactor-plan.md:12-20`.
- Эти условия не остались декларациями, а разложены по фазам и review gates:
  - import/package safety: `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-refactor-plan.md:70-97`, `323-335`
  - shared first slice for CLI + Runtime/MCP: `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-refactor-plan.md:99-139`
  - explicit event/work-state boundary: `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-refactor-plan.md:166-203`
  - anti-dumping-ground rule for `common/*`: `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-refactor-plan.md:62-66`, `337-350`, `355-364`
  - compatibility kept out of canonical Core: `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-refactor-plan.md:62-66`, `126-139`, `259-291`
- План не притворяется завершённой реализацией. Критерии completion сформулированы условно, а не как достигнутый факт: `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-refactor-plan.md:352-364`. Migration report тоже описывает допустимые и недопустимые виды extraction, а не утверждает, что Core уже создан: `.pf/artifacts/python-core-refactor-phase-a-20260814/migration-report.md:198-227`.
- Первый slice явно помечен как `behavior-preserving` и ограничен Process Definition domain: `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-refactor-plan.md:91-97`, `119-139`; `.pf/artifacts/python-core-refactor-phase-a-20260814/migration-report.md:202-206`, `219-227`.
- Требование “один и тот же Core для CLI и Runtime/MCP” опирается не только на план, но и на текущую структуру кода:
  - launcher уже thin: `bin/pf.py:26-41`
  - runtime CLI уже thin delegates: `tools/processforge.py:18384-18507`
  - runtime host уже вызывает `core.resolve_process_definition(...)`: `tools/pf_runtime/host.py:103-155`
  - read-only Runtime/MCP surfaces уже сходятся в одном host seam: `tools/pf_runtime/host.py:694-759`
- Import-path risk подтверждён исходниками и поэтому корректно вынесен в bootstrap gate:
  - `tools/pf_runtime/codex_hooks.py:19-32`
  - `tools/pf_runtime/mcp_server.py:13-27`

## Условия

1. Нужно синхронизировать target architecture с планом по моменту, когда Runtime/MCP начинают использовать общий Process Definition API. Сейчас target architecture откладывает перевод `mcp_server.py` и `codex_hooks.py` на package imports до отдельного Phase 3: `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-target-architecture.md:375-377`. Но план уже требует в Phase C, чтобы CLI и Runtime/MCP вызывали один и тот же Process Definition API: `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-refactor-plan.md:135-139`. Это надо либо явно согласовать, либо зафиксировать, что “shared first slice” считается незавершённым без этого gate.
2. Compatibility boundary нельзя размывать при реализации. Кодовая база уже показывает живой fallback `automation_bindings` -> `technical_obligations` в runtime host: `tools/pf_runtime/host.py:149-151`, и предупреждения по `gates` / `technical_obligations` / `handoff_required` в process validation: `tools/processforge.py:14317-14341`. План это учитывает, но реализация должна держать это вне canonical Core.
3. Event/work-state boundary действительно требует отдельного slice, потому что host уже держит mutable state и event ingress join-point: `tools/pf_runtime/host.py:23-27`, `556-586`, `694-759`. План это фиксирует правильно; отклоняться от этого нельзя без нового review.

## Итог

Как планирующий пакет артефактов, Phase A проходит проверку: пять условий review стали явными gates/deliverables, completion не заявлен преждевременно, а первый slice описан в правильной сохранной рамке. Статус остаётся `pass_with_conditions`, потому что перед кодом нужно устранить расхождение между target architecture и refactor plan по тому, когда именно Runtime/MCP обязаны перейти на тот же Process Definition API, что и CLI.