# Windows cleanup для read-only generated Git objects

Дата: 2026-08-21

`safe_remove_generated_path` в `tools/processforge.py` усилен повторной попыткой
удаления только для разрешённых generated paths: перед retry снимается атрибут
read-only с вложенного файла или каталога. Это покрывает оставленные staging
копии с `.git/objects`, не расширяя допустимую область очистки.

Проверка выполнена на реальном старом stage-каталоге:

`python bin/pf.py clean --root . --release`

Команда удалила застрявший generated stage и не сигнализировала ошибку доступа.
Полный `release-test --public` выполняется в отдельной копии, поэтому не удаляет
runtime-артефакты активного рабочего дерева.
