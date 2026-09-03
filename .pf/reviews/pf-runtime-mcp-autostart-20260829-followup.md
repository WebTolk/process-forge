# Assurance follow-up: pf-runtime-mcp-autostart

## Итоговый статус: PASS ✅

### Проверка цели
- **Средняя находка (`codex-mcp status` игнорировал явный `--python`)** — **исправлена**.
- **Риск регресса поведения по умолчанию (совместимый launcher без `--python`)** — **не выявлен**.

### Ключевые проверки

- `tools/pf_runtime/codex_mcp.py`
  - В `transport_drift()` добавлена логика:
    - `strict_python_command=False` (режим по умолчанию): допускается совместимый лаунчер (`python`, `python.exe`, `py`, `py.exe`) через `compatible_python_command()`.
    - `strict_python_command=True` (когда передан `--python`): используется `exact_command_match()`, то есть сравнение точного пути/имени исполняемого файла.
  - Это означает:
    - без `--python` поведение совместимости сохранено;
    - с `--python` теперь фиксируется именно пиннинг Python.

- `tools/pf_runtime/codex_mcp.py` (вызовы `status_payload`)
  - `strict_python_command=bool(args.python)` в `command_status/install/remove` корректно переключает строгую/нестрогую проверку в зависимости от явности аргумента.

- `tools/smoke_runtime_mcp_autostart.py`
  - В наличии контрактный тест:
    - `transport.command="python"` с `python_executable="python.exe"` → статус `installed` (режим совместимости).
    - явный pin `pinned_python` + `strict_python_command=True` → дрейф `transport.command` детектируется.
    - тот же pinned python в мок-ответе + `strict_python_command=True` → статус `installed`.

- Документация
  - `docs/getting-started/runtime-autostart.md` и `docs/ru/getting-started/runtime-autostart.md` отражают разделение:
    - отдельный поток `Codex MCP` от runtime autostart;
    - `--python` как явный pin для MCP registration;
    - `status` детектирует drift по несоответствующему команду при использовании pin.

### Заключение
- Средняя находка закрыта корректно: явный `--python` теперь проверяется строго и детектирует дрейф.
- Никаких признаков регресса базового поведения без `--python` не обнаружено.
- Изменения в рамках цели не затрагивают планировщик runtime и не меняют его контракт запуска.