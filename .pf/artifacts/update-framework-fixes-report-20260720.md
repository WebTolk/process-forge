# Update Framework Fixes Report - 2026-07-20

Worker: `Darwin` / `worker-update-framework-fixes`
Assignment: `task-001-fix-update-framework-validation`

## Исправлено

- `UF-AUD-001`: `pf update manifest validate` теперь сначала проверяет
  normalized manifest по `schemas/normalized-update-manifest.schema.json`, затем
  выполняет дополнительные Python-проверки.
- `UF-AUD-002`: `sha256` в normalized manifest обязателен и проверяется как
  64-символьный hex digest.
- `UF-AUD-003`: remote artifact URL по умолчанию должен быть HTTPS; `http://`
  допускается только при явном `trust.require_https: false`; `file://`
  допускается как локальный artifact URL.
- `UF-AUD-004`: source URL validation теперь требует корректный remote URL со
  scheme и host; `https:/bad` больше не проходит.
- `UF-AUD-005`: `priority` для global bootstrap sources обязателен и в schema, и
  в Python validator.
- `UF-AUD-006`: `headers_env`, `query_env`, `custom_headers_env` принимают только
  имена env-переменных или `auth_ref:`/`secret_ref:` ссылки; raw-looking значения
  вроде `Bearer raw-token` отклоняются.
- `UF-AUD-008`: добавлена `schemas/update-site-overrides.schema.json`, template
  подключён к schema validation, semantic validation запускается при rebuild
  derived update sites.
- `UF-AUD-009`: `docs/concepts/processforge-self-update.md` теперь явно
  разделяет `self-update-check` как local-index surface и `pf update ...` как
  read-only registry/manifest surface.
- `UF-AUD-011`: entity schemas выровнены по набору `updateSite` url/env/auth
  полей.
- `UF-AUD-012`: `task-create` DeprecationWarning исправлен через
  `re.split(..., maxsplit=1)`.

## Намеренно отложено

- `UF-AUD-007`: `installed-subjects.yaml` не превращён в полноценный
  install/discovery source-of-truth, потому что это потребовало бы механик
  установки, которых нет в read-only slice. Добавлена безопасная минимальная
  интеграция: если scanned manifest уже найден, matching installed-subject record
  может уточнить installed version в derived update site.
- `UF-AUD-010`: полный generic update CLI (`discover`, `download`, `install`,
  `rollback`, `notify`) не добавлялся. Документация фиксирует, что текущий
  `pf update ...` слой read-only и не делает network fetch/download/install.

## Regression Smoke

Добавлен `tools/smoke_update_framework_validation.py` и включён в
`release-test`.

Покрыты бывшие false PASS:

- incomplete normalized manifest без schema-required version fields
- invalid artifact `sha256`
- insecure artifact `http://` без trust exception
- malformed source URL `https:/bad`
- missing bootstrap source `priority`
- raw-looking `headers_env.Authorization`
- raw-looking override `preserved_local.headers_env.Authorization`

Также проверяются допустимые cases:

- valid normalized manifest
- valid bootstrap source
- explicit local trust exception for `http://` source/artifact через
  `trust.require_https: false`

## Проверки

Прошли в основном контексте после review:

- `python -m py_compile tools\processforge.py tools\validate-process-forge-schemas.py tools\smoke_update_framework_readonly.py tools\smoke_update_framework_validation.py bin\pf.py`
- `python tools\validate-process-forge-schemas.py --root .`
- `python tools\validate-public-cleanliness.py --root .`
- `python tools\smoke_update_framework_readonly.py`
- `python tools\smoke_update_framework_validation.py`
- `python tools\validate-process-forge-checksums.py --root .`
- `python bin\pf.py release-test --root .`
- `git diff --check`

`release-test` теперь явно выполняет `smoke_update_framework_validation` и
завершается `RESULT: PASS`.
