# T07: журнал архитектурных решений

Статус всех решений: proposed для будущей реализации; согласованность проверяется в T07 как документация. Это не выпуск API и не конфигурация запущенного executor.

| ID | Решение | Причина и последствие |
|---|---|---|
| D01 | Core владеет policy/projection, adapters только transport и capabilities | Одинаковые правила для local/remote provider; provider label не даёт доступ |
| D02 | `payload_only`, `mediated_session`, `isolated_local` различаются явно | Успех первой фильтрации не доказывает контроль сессии |
| D03 | Egress-bound Work использует successor contract v2 | Security intent нельзя расширить неприкреплённой настройкой или правкой v1 capsule |
| D04 | Allowlist projection и private handle map | Local manifest нужен launcher, но не должен целиком отправляться модели |
| D05 | Full-unit classification и fail-closed unknown | Prefix scan, binary passthrough и неограниченный streaming не дают заявленной гарантии |
| D06 | Durable authorization до send, явный `delivery_unknown` | Исключить неучтённую выдачу и ложную exactly-once семантику |
| D07 | Export только производный artifact | Сохранить provenance/immutability и честный исторический doctor outcome |
| D08 | Отдельная qualification backend/OS; неподтверждённые routes unsupported | Флаг конфигурации не равен закрытому сетевому/файловому каналу |
| D09 | Narrow false-positive exception; обязательный смысл сохраняется либо block | Снижение ложных срабатываний не расширяет scope и не изменяет задачу незаметно |
| D10 | Один назначенный backend/ОС в первом срезе; остальные явно unsupported | Проверяемая область гарантий и отдельная оценка расширения |

Вопросы будущего implementation intake: целевая ОС/backend и возможность закрыть обходы; доверенный recipient registry; минимальный detector corpus и policy owner; допустимые task transformations; retention/ACL требования. Они не препятствуют design delivery: безопасный исход при отсутствии ответа — отсутствие capability и block строгого запуска. Оценка в implementation-plan содержит ограничения и отдельный feasibility этап. Ни один нерешённый вопрос не разрешает неявно ослабить политику.
