# Реализация и проверки
Меняем5текстов согласованными параграфами и точными ссылками на existing concepts; переносим4CHANGELOG пункта изUnreleased в1.2.0 и добавляемSQLite. Указываем дату текущего кандидата2026-10-17, не выдавая её за публикацию.
Inventory штатно регенерируется; expected diff ограничен5записями. Перед commit проверяем ссылки, bilingual content, Git whitespace и source executable parity сd5947ea. Public validators запускаем на чистой candidate-копии с обычным OS TEMP.
Package из committed clean detached worktree, ZIP сравниваем с предыдущим: допустимы5docs+inventory+generated core manifest. Native archive quick включает bootstrap/replay/ingress/conversation public checks; исходные таймауты не повышаем. Raw logs и ZIP retained; лишние собственнойcandidate/extracted copies удаляем лишь после exact path/clean/hash проверки.
После qualification native stages/doctors, обаdev remote SHA readback, новый task-owned handoff.
