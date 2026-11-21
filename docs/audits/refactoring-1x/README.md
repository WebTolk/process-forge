# Роадмап рефакторинга ProcessForge 1.x

Аудит `336b61d470c2a68b4091e6667921a22ecf135ce5` в `dev` после #119 и #120. Цель — продолжить перенос активных обязанностей в существующие слои Core и сохранить публичный договор CLI, MCP и pf-app-server. Публичный рефакторинг состоит из проверяемых срезов с одним владельцем, применимыми платформами и проверкой реального потребителя.

[Карта компонентов](components.md) · [Совместимость](compatibility.md) · [Сверка прежних решений](findings.md) · [Указатель модулей](modules.csv) · [Отслеживание в GitHub](https://github.com/WebTolk/process-forge/issues/132)

## Очередность

1. **P1 — восстановление данных, изоляция и подключённые клиенты.** Первый Work — #121. В этой же группе #122 и #123. Фиксация контрактных сценариев идёт до первого затрагивающего их OOP-переноса.
2. **P2 — проверяемые внутренние владельцы и работа на длинной истории.** Сначала замерить затронутый путь. Раздельно проверить routing history, pending start, objective lookup и физическую активность. Для следующего активного call site брать готовый Core owner и уменьшать зависимость потребителя.
3. **P3 — границы обслуживания и развитие жизненного цикла.** Старые карточки сверять с уже поддерживаемыми функциями. Для read/write разреза на общем индексе измерить цену, сохранить режимы обслуживания, а новый публичный сценарий обосновывать отдельно.

Версии ниже задают целевой порядок. Исправления, совместимые с 1.3.0, могут пройти отдельный patch раньше по SemVer. `dev`, публичный архив, установленный Core и live Runtime/MCP остаются разными проверяемыми состояниями.

## Минорные версии

### 1.4.0 — Совместимость и надёжность

Границы CLI, MCP и pf-app-server и исправления эксплуатации 1.x. Откат, outbox, локальный Runtime, корректный выбор и публикация обновления. Совместимые исправления могут выйти раньше отдельным patch-релизом. [Milestone 1.4.0](https://github.com/WebTolk/process-forge/milestone/2)

| Приоритет | Задача | Результат |
| --- | --- | --- |
| P1 | [#121](https://github.com/WebTolk/process-forge/issues/121) | Откат пакета после обновления кандидатов |
| P1 | [#122](https://github.com/WebTolk/process-forge/issues/122) | Отдельная и целостная доставка каждого target |
| P1 | [#123](https://github.com/WebTolk/process-forge/issues/123) | Единая граница loopback для Runtime-клиентов |
| P1 | [RF14-CONTRACT · #133](https://github.com/WebTolk/process-forge/issues/133) | Сохранить измеримый паритет перед первым переносом активного владельца |
| P2 | [#126](https://github.com/WebTolk/process-forge/issues/126) | Самая новая разрешённая версия после применения политики |
| P2 | [#127](https://github.com/WebTolk/process-forge/issues/127) | Права POSIX при замене Core и восстановлении |
| P2 | [#73](https://github.com/WebTolk/process-forge/issues/73) | Проверка необоснованных литералов на текущем delta |
| P2 | [RF14-ENTRY · #134](https://github.com/WebTolk/process-forge/issues/134) | Устранить записываемую CLI строку повреждённой кодировки 232 307 байт |
| P3 | [#128](https://github.com/WebTolk/process-forge/issues/128) | Предпросмотр update apply без записей |

### 1.5.0 — Core вместо обратных вызовов фасада

Малые OOP-срезы Work, project search и Runtime Host; текущее состояние и история; проверяемый паритет с 1.4 по CLI, MCP и pf-app-server. [Milestone 1.5.0](https://github.com/WebTolk/process-forge/milestone/3)

| Приоритет | Задача | Результат |
| --- | --- | --- |
| P2 | [#108](https://github.com/WebTolk/process-forge/issues/108) | P37 F01–F05, узкие зависимости Work и измерения |
| P2 | [#124](https://github.com/WebTolk/process-forge/issues/124) | Доступность запуска на большой истории сессий |
| P2 | [#125](https://github.com/WebTolk/process-forge/issues/125) | Проверка pending Work start без полного обхода истории |
| P2 | [#72](https://github.com/WebTolk/process-forge/issues/72) | Измерения чтений в CLI, MCP и Runtime |
| P2 | [RF15-SEARCH-CONTEXT · #135](https://github.com/WebTolk/process-forge/issues/135) | Убрать один активный возврат в legacy при проверке project search |
| P2 | [RF15-HOST-STATE · #136](https://github.com/WebTolk/process-forge/issues/136) | Один read-срез для /work-state с явными источниками фактов |

### 1.6.0 — Владение версиями и обслуживанием

Закреплённые версии знаний, совместимая квалификация Workplace-миграций и явное обслуживание общего FTS. Срезы package update apply и индекса на подтверждённых контрактах. [Milestone 1.6.0](https://github.com/WebTolk/process-forge/milestone/4)

| Приоритет | Задача | Результат |
| --- | --- | --- |
| P2 | [RF16-UPDATE-APPLY · #137](https://github.com/WebTolk/process-forge/issues/137) | Ограничить CLI представлением результата после исправления истории и preview |
| P3 | [#129](https://github.com/WebTolk/process-forge/issues/129) | Удержание версий знаний активных Work с немедленным отзывом доступа |
| P3 | [#4](https://github.com/WebTolk/process-forge/issues/4) | Квалифицировать существующий Workplace updater на поддерживаемой матрице |
| P3 | [#5](https://github.com/WebTolk/process-forge/issues/5) | Квалифицировать существующее обслуживание полного Workplace FTS |
| P3 | [RF16-SEARCH-STORAGE · #138](https://github.com/WebTolk/process-forge/issues/138) | Один внутренний SQL-срез по границе read/write с измерением стоимости |

## Порядок и критерии выхода

| Версия | Зависимость и критерий |
| --- | --- |
| 1.4.0 | Точные паритетные fixtures и обязательные дефекты 1.3 с воспроизведением на Windows/Linux. Upgrade и rollback проверены на данных предыдущего поддерживаемого стабильного релиза. Проверены штатный outbox, CLI, Garage и Forge MCP и серверный lifecycle. |
| 1.5.0 | Использовать принятый baseline 1.4 и подтверждённые Work guards. #108 F01 согласуется с Host-срезом. Checker project search сохраняет #120. #124/#125 измеряют собственные наборы данных, #72 фиксирует повторные чтения. Каждый перенос отключает ровно выбранный legacy call и публикует доказательство паритета. |
| 1.6.0 | После починки текущих update records проверить candidate/rollback и конкретный apply pipeline. Для pinned knowledge связь сохраняется до освобождения версии, отзыв действует сразу. Обслуживание Workplace и поиск сохраняют one store, UUID, dataset scope и режимы CLI. Исторические #4/#5 закрываются после проверки фактической приёмки. |

## Как принимать срез

- Указать действующий use case, владельца данных и вызов до переноса. Определить эффект, результат, ошибки, текущую запись и восстановление.
- Использовать композицию малых конкретных служб и подходящие готовые helpers. Protocol уместен при используемой границе. Зафиксировать отсутствие возврата перенесённой обязанности в фасад по настоящему входу.
- После паритета на native Windows/Linux проверить свою матрицу совместимости и оформить независимый вердикт. Путь поставки source → archive → install → Runtime → подключённый клиент применяется по затронутому контракту. [Матрица](compatibility.md)
- Сохранить issue и Work как отдельные единицы. Issue отражает общий результат и критерии. Для начала реализации выбирается отдельный точный Work с разрешённой областью, текущей базой и pin.
