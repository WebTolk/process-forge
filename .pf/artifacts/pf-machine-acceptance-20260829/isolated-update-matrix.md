# Изолированная матрица обновлений `pf-isolated-update-matrix-20260829`

## Результаты проверки

| Шаг | Ожидание | Фактический результат | Уровень | Артефакты/критерий |
|---|---|---|---|---|
| Проверка исходного архива | 1.1.0 zip существует с ожидаемым SHA-256 `fd4c9948de1270a2b836c19796b6882ab994ec61dde854a44403f949661f43dc` | Зафиксирован | PASS | `dist/processforge.zip` |
| Проверка candidate-архива | 1.2.1 zip для приёма из `C:\Users\musst\AppData\Local\Temp\pf-machine-acceptance-20260829-release\processforge-1.2.1.zip` | SHA-256 соответствует ожидаемому `fc79ce7f1fb21ac1fa80acf21e2dc673847510b86aa719d1fda09a965384a767` | PASS | `hardening-report.md`, `certutil` в рабочей сессии |
| Отслеживание статуса без изменений | `core-update status` не должен писать в исходник | Статус `installed`, версия `1.1.0`, `file_count: 868`, `incomplete_update:false` | PASS | `.pf/tmp/pf-machine-acceptance-20260829/work/base` |
| Планирование 1.1.0 → 1.2.1 | `core-update plan` без мутаций | `status: planned`, блокеров нет, `changed` > 0 | PASS | `.pf/tmp/pf-machine-acceptance-20260829/work/base` |
| Применение без `--confirm` | Должен быть запрещён | Ошибка/код `confirm_required` | PASS | `core-update apply` (без флага) |
| Применение с `--confirm` | Обновление до 1.2.1 успешно | `status: applied`, создан backup-dir, изменение версии | PASS | `.pf/tmp/pf-machine-acceptance-20260829/work/base` |
| Локальные изменения блокируют apply | При локально изменённом PF-файле apply назад к 1.1.0 без форса блокируется | `plan` даёт blocker `locally_modified` для `README.md`; `apply` без `--force-local-modifications` → `plan_blocked` | PASS | `.pf/tmp/pf-machine-acceptance-20260829/work/base` |
| Принудительный rollback | С `--force-local-modifications` блок должен сниматься | `apply --confirm --force-local-modifications` успешно возвращает 1.1.0 | PASS | `.pf/tmp/pf-machine-acceptance-20260829/work/base` |
| Повреждённый архив | Планирование должно отвергаться | `core-update plan` → `error=archive_invalid`, сообщение `Not a valid zip file` | PASS | `.pf/tmp/pf-machine-acceptance-20260829/work/bad/processforge-1.2.1-corrupt.zip` |
| Неполное/прерванное состояние | `core-update repair` должен классифицировать как неполное обновление | При создании `runtime/core-update/in-progress.json` → `incomplete_update=true`; `repair` вернул `manual_repair_required` с `in_progress.status=unreadable` | PASS (для повреждённого маркера) | `.pf/tmp/pf-machine-acceptance-20260829/work/base/runtime/core-update/in-progress.json` |
| Режим без последующего вмешательства после очистки маркера | После удаления `in-progress.json` план на `dist/processforge.zip` снова чистый | `status: planned`, `blockers:[]`, `changed:[]`, `locally_modified:0` | PASS | `.pf/tmp/pf-machine-acceptance-20260829/work/base` |
| Финальная целостность PF-файлов | Хэши должны совпасть с baseline 1.1.0 | Сверка по `checksums/processforge.sha256` из `dist/processforge.zip`: `checked 867`, `missing 0`, `hash_mismatch 0`, итог `ALL_MATCH` | PASS | `dist/processforge.zip`, `.pf/tmp/pf-machine-acceptance-20260829/work/base`, `checksums/processforge.sha256` |

## Итог
`pass`: матрица сценариев выполнена без изменений в исходный инсталляционный пакет, с корректной блокировкой без `--confirm`, корректным откатом и восстановлением исходной версии с подтверждением совпадения контрольных сумм.