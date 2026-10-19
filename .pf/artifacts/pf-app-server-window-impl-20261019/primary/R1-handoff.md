# Исправление R1: необязательный вывод не прерывает сервер

Дата: 2026-10-19. Подтверждённое независимое finding R1 (P2, must-fix),
PF message msg_89ce7a820c264cefa38a50f9e7eaea36.

Reviewer воспроизвёл OSError при write и flush TTY: console.py:44-48
выбрасывает исключение до service.command_serve -> runtime.serve, serve_calls=0.
Header стал автоматическим, поэтому отказ относится и к обычному serve без flags.

Primary принимает finding. В своей исходной Work исправляет только console.py:
ожидаемые ошибки записи/flush необязательного представления не блокируют запуск
Runtime. Ошибки самого Runtime и обязательных журналов не скрываются.

Для постоянных проверок основной исполнитель получает отдельную bounded Work
на tools/smoke_server_console.py и собственные R1-test artifacts/tmp/log. Прежний
assurance worker завершил процесс, передал frozen report и явно прекратил правки;
параллельного writer нет. Его прежние reports и исходный public freeze сохраняются.
Новая Work — scoped successor только для тестового файла, без native нового worker.

Проверки: TTY write OSError и flush OSError/ValueError не мешают вызову
RuntimeProcess.serve, не инициируют GUI при утрате вывода, возвращают результат
сервера. Новые regression cases сначала должны показать дефект до исправления.
После изменения повторяем затронутые canonical smokes, обновляем checksum/hash
revision и точную публичную копию, затем передаём R1 patch тому же reviewer.
До независимого повторного обзора не коммитим и не публикуем.
