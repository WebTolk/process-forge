# Обновление checksum inventory

Дата: 2026-08-21

После подтверждённых изменений публичной поверхности inventory обновлён командой
`python tools/validate-process-forge-checksums.py --root . --write`.

Повторная проверка `python tools/validate-process-forge-checksums.py --root .
--check` завершилась успешно. Та же проверка проходит в изолированном public
release-suite. Детерминированный файл inventory: `checksums/processforge.sha256`.
