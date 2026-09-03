# Проверка целевого апдейтера ProcessForge 1.2.1

## Граница проверки

Проверялся апдейтер из собранного архива `processforge-1.2.1.zip` на изолированной копии установленного пакета 1.1.0. Поведение апдейтера из 1.1.0 не используется как критерий готовности: оно оставлено только как свидетельство перехода со старой установки.

Исходные пакеты:

- 1.1.0: `D:\Dev\process-forge\dist\processforge.zip`, SHA-256 `fd4c9948de1270a2b836c19796b6882ab994ec61dde854a44403f949661f43dc`;
- 1.2.1: `C:\Users\musst\AppData\Local\Temp\pf-machine-acceptance-20260829-release\processforge-1.2.1.zip`, SHA-256 `fc79ce7f1fb21ac1fa80acf21e2dc673847510b86aa719d1fda09a965384a767`.

## Результаты

| Сценарий | Фактический результат | Итог |
|---|---|---|
| Чтение версии целевого апдейтера | `1.2.1` | PASS |
| План 1.1.0 -> 1.2.1 | `planned`; added `22`, changed `190`, removed `0`, blockers `0` | PASS |
| Apply без подтверждения | exit `1`, `confirm_required` | PASS |
| Apply с подтверждением | `applied`, установленная версия `1.2.1` | PASS |
| Локально изменённый `README.md` | план содержит один blocker; apply без force: exit `1`, `plan_blocked` | PASS |
| Принудительный откат к 1.1.0 | `applied`, версия `1.1.0` | PASS |
| Точная целостность после отката | проверено `868`; missing `0`; mismatch `0`; файл только из candidate отсутствует | PASS |
| Повреждённый ZIP | exit `1`, `archive_invalid` | PASS |
| Валидный маркер `applying` без достаточного rollback state | exit `2`, `manual_repair_required` | PASS |
| Валидный маркер `failed` с backup и старым manifest | exit `0`, `safe_to_rollback` | PASS |
| Финальный checksum gate | `PASS: checksum inventory matches.` | PASS |

## Вывод

Апдейтер версии 1.2.1 самостоятельно и корректно обслуживает полный цикл обновления и отката установки 1.1.0, блокирует опасные операции и различает автоматическое и ручное восстановление. Изолированный критерий приёмки пройден.

Реальное обновление `D:\.agents\processforge`, проверка Runtime/MCP и последующий возврат этой установки к 1.1.0 остаются отдельным следующим этапом.
