# Финальные исправления документационного аудита Runtime/MCP

## Статус

Выполнено.

## Исправления

- `pf.work.start` отделен от Garage read-tools и описан как governed mutation с
  обязательным непустым `objective`.
- EN Known Limitations синхронизирован с RU по Windows Task Scheduler autostart
  для PF Runtime и host-owned lifecycle stdio MCP.
- В runs/tasks документации абсолютное отсутствие daemon/scheduler заменено на
  точную границу file-first flow и optional PF Runtime service.
- Docstring MCP facade больше не объявляет весь интерфейс read-only.

## Проверки

Финальные проверки выполняются отдельной assurance-задачей после этой правки.
