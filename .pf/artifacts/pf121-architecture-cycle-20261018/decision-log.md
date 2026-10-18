# Решения основного агента

Дата: 2026-10-18. Основание: четыре отчёта, перечисленные в [аудите](architecture-audit.md), исходные архитектурные документы и независимое чтение текущих символов.

| Вопрос | Решение | Обоснование / граница |
| --- | --- | --- |
| Возобновление после сбоя | Прежняя Work/capsule, три живых attempt, только отсутствовавший четвёртый запуск | Native exact state и source freshness подтверждены; новые дубликаты не создавались |
| Следующий перенос | Первым parameter merge/provenance; затем classifier rules и artifact declarations | Связные существующие обязанности, явные consumers, без I/O и новых dependencies |
| Параллельная реализация трёх срезов | Последовательные Work и один writer монолита | Каждый затрагивает `tools/processforge.py`; диапазоны строк не разделяют file scopes |
| ООП и DI | Продолжать явную композицию, узкие Protocol, значения dataclass | Универсальный контейнер не устраняет остаточные callbacks и сейчас не оправдан |
| Общий переход на logging/structlog/Loguru | Не выполнять в текущем рефакторинге | Существующий Logger реализует политики PF; native journals имеют отдельную операционную семантику |
| Рекомендация libraries «operator logging сейчас» | Принять отдельного владельца как кандидата; новые санитарные/retention/квотные правила вынести отдельно | Эти правила меняют observable behavior, а текущая исследовательская Work продукт не пишет |
| psutil | Отложить до конкретного измерительного контракта | Нет текущего продуктового сборщика и доказанного потребителя; нужны units/platform/failure и packaging решения |
| Мастер установки | Общий прикладной сервис и явный интерфейс, в будущей Work | Сохраняются ответы/план/review, прежние CLI-команды и отсутствие новых prompts в automation |
| Исправления старого setup | Не включать автоматически в чистое извлечение | Boolean parsing, force, missing answers fallback и review-to-plan binding меняют действующее поведение |
| MCP descriptions и каталог | Принять замечания; разделять метаданные и чистое выделение каталога | Не менять payload legacy `pf.work_state`; сохранять registry order, action sorting и схемы |
| readOnlyHint у pf.search | Самостоятельное решение о классификации эффектов | Производный index maintenance может записывать SQLite; extraction этого не исправляет |
| Resources/prompts | Resources — отдельный future body-read contract; prompts пока не требуются | Resolve/navigation не дают delivery permission. Нельзя неявно выбирать project/Work или выдавать private roots |
| Веб и несколько устройств | Оставить целевым направлением, сохранять transport-neutral Core | Текущий локальный Runtime и SQLite не доказывают распределённую authority или web management |
| Исторические документы | Сохранять pins; современный дрейф исправлять отдельной навигацией/решениями | Не возвращать старые adapters и storage algorithms ради устаревшего плана |
| Очистка | Удалены шесть проверенных разрешённых целей; dirty stable-preview сохранён | Доказательства релиза и точные Git commits сохранены; force и обход прежних отказов не использованы |

Программа OOP-01–OOP-05 не закрывается. Выбор ближайшего среза не является разрешением расширить его до всего context compiler, новой функциональности или infrastructure work.

Handoff: [implementation-plan.md](implementation-plan.md) задаёт первый проверяемый результат. Перед новым admission перечитать source contracts и существующие assignments, определить единственного writer и закрепить обязательные входы.
