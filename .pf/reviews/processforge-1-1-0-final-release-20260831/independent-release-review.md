# Изолированная release-review ProcessForge 1.1.0

## Вердикт

`pass_with_conditions`

## Проверенная область

- Версия, update index, migration и отсутствие test-only `1.2.x` в stable.
- Garage/Forge boundary и опциональность Codex hooks.
- EN/RU human/agent documentation.
- Schema, checksum, public cleanliness, update, Runtime/MCP, onboarding,
  domain-neutral kernel, process/authoring/evolve suites.

## Доказательства

Полный source public release-test выполнил 185 командных checks: 183 PASS и два
ожидаемых pre-commit FAIL. Первый отказ — clean-Git provenance gate на грязной
рабочей копии; второй — `git diff --check` из-за trailing whitespace в
сгенерированном `.pf` snapshot. Public checks отдельно обнаружили только два
устаревших `dist/processforge-1.1.0.*`, которые по плану заменяются exact-tag
сборкой. Schema, checksum, public cleanliness, release-check, examples-check,
events-validate и doctor-project прошли.

## Обязательные условия выпуска

1. Создать финальный source commit и tag `v1.1.0`.
2. Повторить provenance smoke в чистом worktree exact tag.
3. Пересобрать ZIP/sidecar и пройти полный extracted archive release-test.
4. Создать historical/stable metadata из финального hash/size и пройти
   repository/stable/tag smokes.
5. Выполнить upgrade proof с `1.0.2`.
6. Получить real hosted Codex MCP proof либо явно оставить внешний blocker.

## Ограничение независимости

Review выполнена в отдельной assurance-стадии и не меняла product files, но не
внешним агентом: выбранный ProcessForge process запрещает subagents. Поэтому
это изолированная self-review, а не организационно независимая экспертиза.
