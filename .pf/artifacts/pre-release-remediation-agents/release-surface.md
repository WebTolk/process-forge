# Отчёт агента: release checksum и installation surface

- Assignment: `remediation-release-surface-20260730`
- Run: `pre-release-remediation-20260730`
- Agent: `codex-remediation-release-surface`
- Session: `pre-release-remediation-20260730-release-surface`
- Lease: `lease-remediation-release-surface-20260730`
- Завершено: `2026-07-30T07:14:07Z`
- Статус: implementation complete; ожидается интеграция и финальное обновление checksum inventory

## Закрываемые findings

### PF-AUD-015 — embedded checksum surface

Исправлена логика формирования checksum inventory:

- в корневую release surface добавлены `README.ru.md`, `QUICKSTART.ru.md` и
  `.gitignore`;
- сохранено покрытие `packs/`;
- добавлено архивное имя `AGENTS.md`: в source checkout оно получает checksum
  канонического `.pf/AGENTS.md`, а в распакованном архиве — собственного
  `AGENTS.md`, в соответствии с precedence `release-pack`;
- `checksums/processforge.sha256` по-прежнему исключён как self-referential;
- публичная функция `public_files()` сохранена как compatibility view без
  дублирования source path.

Targeted smoke сопоставляет checksum selection с фактическим
`release_source_files`/release-ignore/forbidden contract. На текущем
параллельно изменяемом дереве совпали все `783` поставляемых entry, кроме
самого checksum inventory: `missing=[]`, `extra=[]`.

### PF-AUD-024 — installation/first-run documentation slice

Обновлены английские и русские `installation.md` и `first-run.md`:

- после `cd process-forge` mutable workplace и проект создаются в sibling
  roots `../pf-workplace` и `../my-project`, а не внутри заменяемого
  дистрибутива;
- production software flow задан как
  `workplace-init --profile software-development`, затем отдельный
  `project-onboard`;
- явно указано, что `first-run` не поддерживает `--profile`;
- перед project-local launcher добавлен переход `cd ../my-project`.

## Изменённые файлы

- `tools/validate-process-forge-checksums.py`
- `tools/smoke_remediation_checksum_surface.py`
- `docs/getting-started/installation.md`
- `docs/getting-started/first-run.md`
- `docs/ru/getting-started/installation.md`
- `docs/ru/getting-started/first-run.md`

Main CLI, checksum inventory, `dist/**` и `updates/**` не изменялись.

## Проверки

PASS:

```text
python -m py_compile tools/validate-process-forge-checksums.py tools/smoke_remediation_checksum_surface.py
python tools/smoke_remediation_checksum_surface.py --root .
PASS: checksum selection matches 783 release-pack entries excluding the inventory itself
PASS: shipped checksum surface covers root aliases, public directories, and stale-file detection.
```

Дополнительная проверка документации подтвердила во всех четырёх файлах:

```text
../pf-workplace
../my-project
workplace-init --workplace ../pf-workplace --profile software-development --apply
project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --apply
```

`git diff --check` для owned files прошёл. Serena была вызвана первой, но
symbol extraction для Python недоступен (`Active languages: []`); после
Serena pattern search использован shell fallback.

Ожидаемые/внешние результаты:

- `validate-process-forge-checksums.py --check` сейчас возвращает `1`, потому
  что inventory намеренно не обновлялся во время параллельной реализации;
- общий `validate-public-cleanliness.py` возвращает `1` на новых
  `smoke_remediation_*` других assignments (Windows-path fixtures и
  policy-neutrality fixtures). В owned files этого assignment violations нет.

## Отложенные финальные шаги

После freeze и объединения всех remediation slices release owner должен:

1. обновить `checksums/processforge.sha256` через `--write`;
2. выполнить `--check`;
3. убедиться, что checksum paths в точности равны финальному release-pack
   surface без `checksums/processforge.sha256`;
4. только затем пересобрать и проверить `dist/processforge.zip`.

Полный release test и сборка архива в этом assignment не запускались согласно
write-scope и запрету преждевременного refresh.
