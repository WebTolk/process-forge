Статус: ready_for_review.

Продуктовая область Windows-воркера:

- tools/pf_runtime/windows_console.py — новый адаптер minimize_console() -> str.
- tools/pf_runtime/windows_autostart.py — только runtime_action: прямой CLI и --minimized.

Сопровождение: собственный журнал Windows-воркера, этот список, change-summary.md,
verification.md и итоговый report.md, получаемый через захват финального ответа.
Изолированные проверочные сценарии и их результаты сохранены в области .pf/tmp
Windows-воркера как воспроизводимое свидетельство; общие smoke-файлы не изменялись.
