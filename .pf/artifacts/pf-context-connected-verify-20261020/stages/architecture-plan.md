# План документальной приёмки

architecture: продуктовые owner modules остаются прежними; итог — переносимая
сводка comparison.json, provenance.json и report.md, точные приватные ответы
в собственном retained scratch и native lifecycle receipts.

implementation-plan: 1) проверить структурированное равенство проекций и hashes;
2) связать source review и device proof с новым connected-host наблюдением;
3) выполнить native task-complete одной исторической карточки; 4) проверить
защиту снимка и index; 5) завершить assurance, доставить отдельный коммит в оба dev.
Рабочий index не используется для коммита: отдельный index начинается от HEAD
и включает лишь собственные разрешённые пути. Приватные process paths не коммитятся.

decision-log: Python QA для продукта not_applicable — исполняемый продуктовый код
не меняется. Scratch сборщик не входит в дистрибутив. Исторические source проверки
не повторяются без изменения bytes. Результат не объявляет готовность всей альфы.
Scope исторической карточки закрывается штатной командой, immutable history сохраняется.

architecture-plan-ready: методы чтения и native dry-run доступны; данные уже
сохранены и достаточны, дальнейший шаг не требует инфраструктурных действий.
Handoff: implementation запишет сопоставление и закроет одну карточку нативно.
