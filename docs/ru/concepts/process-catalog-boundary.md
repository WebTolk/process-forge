# Граница каталога процессов

Основной каталог содержит только предметно-нейтральные процессы: управление
ресурсами, authoring, инициализацию, context resolution, оркестрацию,
supervision, обновления и универсальное выполнение задач.

Предметные процессы сохранили стабильные идентификаторы, но перенесены в
необязательные примеры:

- `examples/domain-packs/software-web`
- `examples/domain-packs/content-workflow`
- `examples/domain-packs/verification-workflow`

Они помечены как `optional_example`, не устанавливаются при инициализации
рабочего места и не входят в каталог по умолчанию. Рабочее место или проект
может явно импортировать pack и зарегистрировать его процессы, prompts,
knowledge packages, capabilities и classifiers через обычные resource-данные.

Универсальные runtime-механизмы при этом остаются в `process-forge-core`.
