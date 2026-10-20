# Замороженный source candidate

changed-files: VERSION, common/release_identity.py, один import Path в smoke
(с сохранением вызова loader), CHANGELOG, EN/RU alpha notes и шесть собственных
inventory rows. source-candidate.json фиксирует точные hashes.
change-summary: реальная версия 1.3.0-alpha1; накопленный принятый checkpoint
описан без заявления о завершении всего OOP. Source commit отдельно доставляется
в оба dev, clean checkout строится из exact commit, не из рабочего дерева.
implementation-scope-respected: guards stable manifest, OOP и snapshot сохранены;
product delta только разрешённый. Focused Ruff/format/mypy двух Python файлов
и исправленный existing runtime policy smoke PASS. Полные gates ещё не заявлены.
Handoff: code-assurance выполняет source release-test/supervisor-stress и focused
pytest на окончательном чистом source; архив пока не собирается и не публикуется.
