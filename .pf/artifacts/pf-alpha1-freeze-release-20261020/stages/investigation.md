# investigation — freeze alpha1

investigation-report: прочитаны docs/maintainers/release-publishing.md и release-checklist.md; предыдущие release evidence подтверждают зеркальные immutable assets. Common release identity сейчас 1.2.0. Предыдущий cumulative source gate остановился на отсутствующем pathlib.Path в одном smoke; исправление ограничено import. Prerelease selection fix уже принят и проверен.

impact-analysis: schema/process/startup-contract versions независимы и сохраняются. Источник будущего ZIP — clean checkout exact source commit, без чужого рабочего слоя. Старый stable manifest сохраняется побайтно; новый alpha документ появляется после получения actual asset URL/hash. GitVerse token берётся из окружения, секрет не пишется в URL/argv/logs.

Локально разрешены Python/packaging docs; существующий maintainer contract требует source gates. Требование archive-test сужено действующим прямым запретом пользователя: сам build и проверка опубликованных byte hashes допустимы, содержимое ZIP не открывается.

investigation-complete: минимальные blockers и release mechanism известны. impact-understood: source/archive/install/host evidence различаются; device acceptance не заявляется. Handoff: domain закрепляет prerelease каналы и immutable bytes.
