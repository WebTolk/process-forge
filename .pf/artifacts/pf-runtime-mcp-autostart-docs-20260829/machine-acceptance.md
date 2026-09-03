# Машинное acceptance: PF Runtime autostart и Codex MCP

## Итог

Статус: `pass_with_conditions`.

На машине реально установлен и запущен current-user Windows Task Scheduler task
для PF Runtime. Codex MCP зарегистрирован как host-owned stdio server и не
запускается отдельным системным autostart-механизмом.

## Runtime autostart

Проверено 2026-08-29 15:58 +04:00:

- task name: `ProcessForge Runtime 5365635d5b5e`;
- Task Scheduler state: `Running`;
- last result: `267009` (`SCHED_S_TASK_RUNNING`);
- missed runs: `0`;
- autostart status: `installed`;
- drift: отсутствует;
- owner model: current user, logon trigger, least privilege;
- action: точный Python executable запускает
  `D:\.agents\processforge\bin\pf.py runtime serve`;
- working directory: `D:\.agents\processforge`;
- workplace: `D:\.agents\processforge-workplace`.

Живой Runtime:

- endpoint: `http://127.0.0.1:59082`;
- status: `ready`;
- PID: `3828`;
- installed Core: `1.1.0`;
- scheduler result: `ok`; director, inspector, ledger и projection jobs имеют
  свежие успешные ticks.

`health: degraded` вызван известным timeout status-probe в установленном 1.1.0,
а не отказом Task Scheduler или остановкой scheduler jobs.

## Codex MCP

- registration name: `processforge`;
- transport: `stdio`;
- command: `python`;
- server: `D:\.agents\processforge\tools\pf_runtime\mcp_server.py`;
- workplace argument: `D:\.agents\processforge-workplace`;
- PF status: `installed`, drift отсутствует;
- owner: `codex-host`;
- system autostart: `false`.

Во время независимого reviewer-run MCP process имел родителя `codex.exe`. После
завершения host session процесс штатно завершился. Старый manual orphan MCP
PID `13356` и его launcher PID `10680` удалены; на финальной проверке idle MCP
processes отсутствуют. Регистрация сохранена и следующая Codex host session
запустит новый подключенный stdio process.

## Проверки source candidate

- Python compile новых Runtime/MCP модулей: PASS.
- `tools/smoke_runtime_mcp_autostart.py`: PASS.
- `release-test --only smoke_runtime_mcp_autostart --no-clean`: PASS.
- `tools/smoke_mcp_codex_contract.py`: PASS до текущего documentation run.
- Runtime autostart remove dry-run: `operation=remove`, `applied=false`.
- Runtime autostart повторный install: `operation=unchanged`, `applied=false`.
- Codex MCP remove dry-run: `operation=remove`, `applied=false`.
- Codex MCP повторный install: `operation=unchanged`, `applied=false`.
- public cleanliness: PASS.
- все локальные Markdown links под `docs/`: PASS.
- stale Runtime/MCP documentation claim scan: PASS.
- `git diff --check` целевых файлов: PASS; остаётся предупреждение о будущем
  CRLF-to-LF преобразовании `tools/processforge.py`.

Assurance finding по явному `codex-mcp --python` исправлен: default-compatible
launcher остаётся accepted, explicit executable pin обнаруживает command drift,
exact pin принимается. Regression smoke проходит.

## Условия и остаточные риски

1. Установленный дистрибутив остаётся на `1.1.0`. Новые management commands
   `runtime autostart` и `codex-mcp` реализованы в source checkout и ещё не
   доставлены установленной версии. Уже созданный scheduled action использует
   поддерживаемый установленным 1.1.0 `runtime serve`.
2. Полный `smoke_long_lived_runtime.py` запускался дважды ранее в этой работе и
   не прошёл: сначала Windows path normalization вокруг `.ingress.lock`, затем
   restart завершился с code 1. Это отдельные Runtime defects; autostart task при
   реальном запуске работает.
3. Logon-trigger проверен через реальный Task Scheduler registration и manual
   `schtasks /Run`; полный reboot/logoff в этом run не выполнялся.
4. Изменения source checkout не закоммичены и не упакованы в release.
