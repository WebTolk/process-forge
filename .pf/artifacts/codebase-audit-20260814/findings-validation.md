# Поведенческая проверка выводов аудита

Дата: 2026-08-14

## 1. Повторный `worker-run start` — подтверждено

В изолированном временном generic PF-проекте был запущен sleeping shell worker
через `worker-run start --detach`, а затем та же команда для того же task.

```json
{
  "first_rc": 0,
  "second_rc": 0,
  "first_pid": 19912,
  "second_pid": 15296,
  "state": "running"
}
```

Это прямое воспроизведение: второй start не отклонён и заменяет сохранённый PID
в `status.json`. Находка остаётся **высокой**.

## 2. `--wait` — уточнено

Тот же тестовый worker со сном 2 секунды был запущен с `--wait` без `--detach`:
он завершился `exit_code: 0`, `status: completed`, фактическое время команды
составило 4.10 секунды. Значит, пользовательская семантика «ждать завершения»
работает, потому что это уже default.

Поиск implementation не нашёл обращения к `args.wait`; код использует только
`args.detach`. Следовательно, это **низкоприоритетный инертный CLI-флаг**, а не
функциональный defect.

## 3. Ad-hoc driver path — дополнительная подтверждённая находка

В первом варианте изолированного теста `worker-run start --driver <sleeper.yaml>`
запустил процесс успешно, но `execution-inspector-tick --run audit-run` завершился:

```text
FAIL: runtime driver not found: sleeper
```

После start durable state хранит id `sleeper`, а Inspector заново ищет driver по
этому id и уже не знает исходный путь. Это **средняя** ошибка recovery для
ad-hoc path driver; она не касается зарегистрированного `codex-exec`.

## 4. Public gates — подтверждено как условный риск

`release-check --root .` прошёл, но не вывел public-specific проверки.
Отдельный запуск:

```text
release-test --public --only py_compile --no-clean
```

выполнил дополнительно `dist contains no stale ...`, `no parity WARN ...` и
проверку Russian documentation. Поэтому separation существует фактически.
Это не defect текущего кода: риск возникает только при CI, который должен
делать public release, но вызывает лишь `release-check`.

## 5. Исключение `process-forge.local.yaml` — подтверждено как policy choice

Прямой вызов `release_path_is_forbidden()` вернул:

```text
examples/demo/process-forge.local.yaml -> None
templates/demo/process-forge.local.yaml -> None
process-forge.local.yaml -> private local config
```

Исключение существует. Утечка не доказана: `release-check` и
`validate-public-cleanliness` проходят. Нужна лишь явная policy/regression
проверка, если такие fixture-файлы разрешены намеренно.

## Итог

Подтверждены две исправляемые ошибки: duplicate start (высокая) и recovery
ad-hoc driver path (средняя). Остальные выводы скорректированы до CLI debt и
условных policy risks. Продуктовый код не менялся.
