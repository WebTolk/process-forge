# Проверки операторского обновления

Все перечисленные новые нативные команды завершились с exit 0:

| Проверка | Результат |
| --- | --- |
| Core plan непосредственно перед остановкой | 2 added, 9 changed, 1449 unchanged; конфликтов и blockers нет |
| Полное нативное наблюдение перед остановкой | 2 проекта, running=0, complete; leases held=0 |
| Явно разрешённый server stop --force | Штатная остановка успешна |
| Одна попытка core-update apply --confirm | applied; 1.3.0-alpha1 |
| Все установленные управляемые файлы | 1460/1460 SHA-256 и размеры совпадают |
| Резервные копии | 9/9 файлов совпадают с исходными байтами; модель старого манифеста сохранена |
| Конфигурация | Исходный хеш сохранён; valid, интервал 10 секунд |
| Встроенный post-update doctor-workplace | 197 PASS |
| Core status / repair | installed, incomplete_update=false / nothing_to_repair |
| Новый Runtime | После apply, ready/healthy; пять свежих ok jobs |
| Установленный monitor --once и --json | Календарный uptime; числовой uptime_seconds сохранён |
| Видимый интерактивный монитор | Один живой дочерний процесс, exit marker отсутствует |
| Свежий подключённый pf.context | fresh/continue; без обновления snapshot |

Исходники архива совпадают с квалифицированным commit
`99f19b0c32776cd2452f5698b5748751c6587dba`; различия с доставленным
`cc690b263b65daaa0e85a21186de89944b1064a9` затрагивают только `.pf/`.
Хеш установленного monitor.py дополнительно совпадает с sealed manifest.
Архив построен из чистого commit; постороннее dirty/staged состояние
основного checkout не включалось и не проверялось как этот кандидат.

Повторно не запускались ранее пройденные для этих байтов полные проверки:
PF release-test 274/274, public 3/3, supervisor-stress 6/6;
PF Python pytest 142 passed + 42 subtests, 1 skip из-за Windows symlink
privilege. Источник доказательств: предыдущая выполненная uptime-задача,
её test-report.md, code-quality-report.md и sealed candidate manifest.

Проверка не утверждает полноту sessions/work/workers статистики,
перезагрузку текущего MCP-хоста или совпадение встроенных CLI/Runtime
ярлыков с версией архива. Эти наблюдения описаны в report.md.
