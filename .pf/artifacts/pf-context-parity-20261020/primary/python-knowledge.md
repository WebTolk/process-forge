# Разрешённые знания Python и архитектурная сверка

PF Work: pf-context-parity-20261020; resource generations закреплены immutable capsule и native work-resolve.
Прочитаны разрешённые docs.python:root, docs.python-practices:root, docs.python-peps:root; private resolve receipts сохраняют material/metadata fingerprints.
В docs.python/builtins.md проверен контракт open: binary mode сохраняет bytes, text universal-newline reading переводит CRLF/CR/LF; запись с newline=None на Windows преобразует LF. Вывод: для byte proofs читать rb/Path.read_bytes; LF/CRLF сравнение выполнять явно и локально, не менять общую hash-функцию.
Из docs.python-practices применены PEP20 (явная простая зависимость, ошибки не скрываются), typing-guide (конкретные типы входов/результатов); из PEP8 — public/internal interfaces и programming recommendations.
Проверены текущий python-quality-context и общий python/toolchain.json: pytest/Ruff lint+format/mypy обязательны для затронутой области; project config/interpreter имеют приоритет, зависимости Core не устанавливаются.
Все девять закреплённых архитектурных источников перечитаны: clarification, migration-contract, adr/domain/direction, progressive boundary, oop-02/03/05.
Применение: существующие owners, отсутствие обратного пути в Main из Core, явные distribution root/documents/digests; file-only; live reads; никаких новых global caches; raw evidence и public contracts сохранены.
После реализации выполняется повторная сверка по D01-D11/R01-R12 и исходным байтам, независимо от числа классов/строк.

