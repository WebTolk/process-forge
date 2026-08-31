# Финальная квалификация ProcessForge 1.1.0

Вердикт: `pass_with_external_blocker`

## Выпуск подтверждён

- публичная последовательность версий остаётся `1.0.2 -> 1.1.0`;
- `1.2.0` и `1.2.1` удалены из production release/update поверхности и не
  объявляются публичными релизами;
- финальный source commit/tag, детерминированный ZIP, исторический sidecar и
  stable-channel manifest согласованы;
- production manifest использует реальные immutable GitHub Release URL и
  точные SHA-256/size;
- generic project init не устанавливает Codex hooks и не становится
  `repairable` при их отсутствии;
- Codex hooks остаются явной optional host telemetry;
- agent path — `pf.context -> pf.search -> pf.resolve -> pf.work.start`, без
  обычного обслуживания Runtime/MCP/hooks/Ledger/search-index;
- EN/RU Quickstart и concept docs согласованы с Garage/Forge, host-owned stdio
  MCP, Windows-only managed Runtime autostart и отсутствием TUF в 1.1.0;
- source, extracted archive, Windows Runtime/autostart, MCP contracts,
  synthetic 1.1.1 discovery и реальный upgrade 1.0.2 -> 1.1.0 прошли.

## Внешний blocker

В текущем host-сеансе PF MCP не загружен как callable connector, поэтому
реальный свежий hosted-Codex вызов `pf.context`/`pf.work.start` не подменялся
direct-stdio smoke и честно не отмечен PASS. Локальный MCP contract, host-owned
stdio lifecycle, Garage sessionless/session-enhanced и missing-session
diagnostics прошли. Остаточная проверка требует нового Codex host session с уже
зарегистрированным final 1.1.0 MCP.

Blocker внешний и не меняет байты опубликованного Core/ZIP. Это разрешённый
исход Definition of Done: hosted MCP PASS либо явно зафиксированный внешний
blocker.

## Граница рабочего дерева

Релизный source/tag и metadata-срез коммитятся адресно. В основной рабочей
копии сохранены посторонние незакоммиченные `.pf`-материалы предыдущих работ;
они не попали ни в source commit, ни в ZIP, ни в release metadata commit.
