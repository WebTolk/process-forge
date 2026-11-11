# Подготовка агента к разработке PF на новом устройстве

[English](../../contributors/agent-setup.md)

Эта инструкция предназначена для агента, которому поручено после клонирования
ProcessForge подготовить рабочее место с общими знаниями, инструментами и MCP.
Сначала прочитайте корневые [AGENTS.md](../../../AGENTS.md) и
[CONTRIBUTING.ru.md](../../../CONTRIBUTING.ru.md).

Рабочее место PF создаётся отдельно от исходников. Для разработки самого PF
не требуется восстанавливать чужую `.pf`, создавать Work или запускать службы.
Общие пакеты знаний доступны как обычные локальные документы; процессы PF для
подключённых потребительских проектов настраиваются отдельно.

## 1. Проверить исходники и доступ

Подготовьте Git, GitHub CLI `gh`, Python 3.11+ с `pip` и `venv`, оболочку с UTF-8.
Недостающие программы устанавливайте из официальных дистрибутивов или через
системный менеджер пакетов. Проверьте имя и адрес автора Git. Используйте
существующие учётные данные; при отсутствии входа в GitHub выполните
`gh auth login`. Для зеркалирования после слияния понадобится доступ к GitVerse.
Токены хранятся в менеджере учётных данных, не в URL, инструкции или репозитории.

```sh
git clone --branch dev https://github.com/WebTolk/process-forge.git
cd process-forge
git status --short --branch
git remote -v
git fetch origin
git switch -c work/agent-bootstrap origin/dev
gh auth status
git rev-parse HEAD
```

Если репозиторий уже клонирован, сначала сохраните имеющиеся изменения и проверьте
текущую ветку. Канонические remotes и порядок добавления `gitverse` описаны в
CONTRIBUTING. Отсутствие удалённого доступа блокирует публикацию, но не локальную
проверку исходников.

## 2. Выбрать каталоги и Python

Зафиксируйте абсолютные пути этого устройства. Не переносите пути чужого
компьютера и не считайте наличие общего каталога настроек агентов обязательным условием.

| Обозначение | Назначение |
| --- | --- |
| `Repo` | Рабочий клон исходников PF. |
| `Core` | Отдельная установка PF из известного релиза или зафиксированного коммита. |
| `PfPython` | Python внешнего виртуального окружения установленного PF. |
| `DevPython` | Python отдельного окружения разработки исходников. |
| `Workplace` | Изменяемое рабочее место PF, отдельно от Core и исходников. |
| `Tools`, `Toolchains` | Общие инструменты, их окружения и контракты toolchain. |

В командах ниже `<...>` нужно заменить выбранными путями. В PowerShell исполняемый
путь вызывается как `& $PfPython ...`, в POSIX — `"$PfPython" ...`. Пути с
пробелами заключайте в кавычки. Существующую установку сначала проверьте; повторная
инициализация не является обновлением.

Для новой установки Core можно использовать официальный релиз либо отдельный
клон точной исходной ревизии: `git clone --no-hardlinks <Repo> <Core>`, затем
`git -C <Core> checkout --detach <зафиксированный-SHA>`. Рабочая ветка разработки
при этом остаётся в `Repo`.

```sh
python -m venv <окружение-PF>
python -m venv <окружение-разработки>
<PfPython> -m pip install -r <Core>/requirements.txt
<DevPython> -m pip install -r <Repo>/requirements.txt
<DevPython> -m pip install types-PyYAML
<PfPython> <Core>/bin/pf.py version
```

Путь интерпретатора внутри окружения: `Scripts/python.exe` в Windows,
`bin/python` в Linux/macOS. Актуальный `requirements.txt` включает **PyYAML и
jsonschema**. `types-PyYAML` нужен для проверки типов в окружении разработки;
его не следует добавлять в зависимости Runtime.

Проверьте возможности выбранного Python:

```sh
<PfPython> -c "import sqlite3, ssl, zlib, venv, yaml, jsonschema; d=sqlite3.connect(':memory:'); d.execute('create virtual table t using fts5(text)'); print(sqlite3.sqlite_version, ssl.OPENSSL_VERSION); d.close()"
```

Дополнительно выполните проверки из [требований PF](../../requirements.md),
включая `ctypes` на Windows и права на локальное хранилище. Затем для **нового**
рабочего места:

```sh
<PfPython> <Core>/bin/pf.py workplace-init --workplace <Workplace> --profile generic --dry-run
<PfPython> <Core>/bin/pf.py workplace-init --workplace <Workplace> --profile generic --apply
<PfPython> <Core>/bin/pf.py doctor-workplace --root <Workplace>
```

Профиля `generic` достаточно для общих знаний и инструментов контрибьютера.
Пакет процессов `software-development` подключается при необходимости процессов
для потребительских проектов. Он не заменяет GitHub workflow самого PF и не
устанавливает перечисленные ниже Python-пакеты знаний.

## 3. Подключить общие пакеты знаний

Общий перечень, начальные версии и SHA-256 архивов закреплены в
[knowledge-packages.json](../../contributors/knowledge-packages.json).
Это вход установщика и инструкции агента; файл не выдаётся за нативный снимок
контекста PF. Стандартная подготовка устанавливает все пять пакетов:

| ID пакета PF | Репозиторий | Когда использовать |
| --- | --- | --- |
| `docs.python` | [pf-python-knowledge](https://github.com/WebTolk/pf-python-knowledge) | Язык и стандартная библиотека: pathlib, subprocess, asyncio, typing и другие разделы. |
| `docs.python-practices` | [pf-python-practices-knowledge](https://github.com/WebTolk/pf-python-practices-knowledge) | Практические HOWTO, аннотации, типизация и приёмы разработки. |
| `docs.python-peps` | [pf-python-peps-knowledge](https://github.com/WebTolk/pf-python-peps-knowledge) | PEP 8/257, предложения по типизации, упаковке и развитию языка. Проверять статус PEP и применимость к версии Python. |
| `docs.python-packaging` | [pf-python-packaging-knowledge](https://github.com/WebTolk/pf-python-packaging-knowledge) | Окружения, зависимости, pyproject, метаданные и распространение пакетов. |
| `docs.python-devguide` | [pf-python-devguide-knowledge](https://github.com/WebTolk/pf-python-devguide-knowledge) | Справочные практики разработки CPython. Правила CONTRIBUTING самого PF имеют приоритет для его контрибьютеров. |

Начальная публичная версия каждого пакета — `1.0.1`, ID ресурса — `root`.
Это выбранные документы снимков от 2026-10-02, а не полные постоянно обновляемые
зеркала сайтов. Некоторые материалы описывают Python новее минимально
поддерживаемого PF. Исходные URL, даты и лицензии сохранены в документах,
`sources.json` и `NOTICE.md`.

Выполните просмотр плана и установку:

```sh
<DevPython> <Repo>/tools/install-contributor-knowledge.py --workplace <Workplace>
<DevPython> <Repo>/tools/install-contributor-knowledge.py --workplace <Workplace> --apply
```

Установщик работает со стандартным корнем `global`: `<Workplace>/packages`.
Он скачивает ZIP конкретных версий, сверяет SHA-256 и идентичность пакета,
проверяет пути внутри архива и регистрирует точный `install_path` в
`registries/installed-subjects.yaml`, сохраняя посторонние записи. Совпадающий
установленный снимок проверяется и сохраняется. Другую версию или изменённые
материалы он не перезаписывает: для них применяется штатный updater PF.

Для установки без сети предварительно скачайте пять ZIP с именами из профиля и
добавьте `--archives-dir <каталог>`. Проверка закреплённых хешей остаётся
обязательной. Нестандартный корень пакетов требует отдельной явной установки и
правильной записи пути в реестре установленных сущностей.

Для каждого ID выполните:

```sh
<PfPython> <Core>/bin/pf.py knowledge-package-doctor --workplace <Workplace> --package <id> --package-root global
```

Ресурсные индексы уже включены в архивы. После намеренного изменения метаданных
используйте `knowledge-index-refresh --workplace <Workplace> --package <id>
--package-root global --apply`, затем снова проверьте пакет.

При разработке **самого ProcessForge** подбор знаний задают AGENTS и этот общий
профиль. Начинайте с `<Workplace>/packages/<id>/resources/README.md`, затем
открывайте только нужные документы. Архитектуру и публичные контракты PF читайте
в `docs/` текущей ревизии и вложенных `AGENTS.md`.

Для **отдельного потребительского или тестового проекта под управлением PF**
добавьте нужные ID в `requirements.knowledge_packages` его конфигурации. Затем
выполните `project-context-refresh`, `project-context-check`, `search-index
refresh` и `search-index doctor` с явными путями проекта и рабочего места.
Нативный поиск PF ограничен выбранным проектным снимком. Ради него не нужно
создавать приватную `.pf` в репозитории исходников ProcessForge.

## 4. Установить и зарегистрировать Python QA

Используйте поставляемый общий набор и ту же major/minor-версию Python, что у
окружения разработки:

```sh
<DevPython> <Repo>/tools/python-qa/install.py --tools-root <Tools>/python-qa --toolchains-root <Toolchains>
<DevPython> <Tools>/python-qa/qa.py --project-root <Repo> --python <DevPython> versions
```

Набор включает **Ruff, pytest, pytest-cov, coverage.py, mypy, Bandit, pip-audit**,
закреплённые версии, общий launcher и контракт Python toolchain. Прочитайте
[инструкцию набора](../../../tools/python-qa/README.md). Конфигурация проекта
имеет приоритет над общими настройками. Для другой версии Python или ОС нужен
отдельный совместимый набор.

Зарегистрируйте реальные команды через `tool-register --workplace <Workplace>
--id <id> --name <имя> --capability <capability> --command <команда>
--healthcheck <проверка> --apply`:

| ID инструмента | Capability | Операция `qa.py` |
| --- | --- | --- |
| `python-ruff` | `lint` | `lint` |
| `python-formatter` | `format` | `format`; запись изменений — `format-fix` |
| `python-pytest` | `test_running` | `test` |
| `python-coverage` | `coverage` | `test -- --cov=src --cov-branch tests` |
| `python-mypy` | `typecheck` | `typecheck` |
| `python-bandit` | `security_analysis` | `security` |
| `python-pip-audit` | `dependency_audit` | `audit` |

Например, команда lint: `<DevPython> <Tools>/python-qa/qa.py --project-root
<Repo> --python <DevPython> lint`. Для проверки launcher используйте `versions`,
а затем отдельно проверьте нужную операцию. Если выбранный процесс PF разрешает
Git, `gh` и `rg` через реестр инструментов, зарегистрируйте и их. Запись команды
в реестр не устанавливает программу и не подтверждает её работоспособность.

## 5. Установить MCP и подключить настоящий хост агента

Регистрация через PF `mcp-register` описывает сервер в рабочем месте, но сама по
себе не подключает его к хосту. Настройте **тот хост, в котором работает агент**,
сохранив посторонние записи. Используйте абсолютные пути исполняемых файлов:
графическое приложение может не наследовать PATH открытой оболочки.

- **Serena или эквивалентный IDE MCP.** Это основной способ поиска символов и
  ссылок в коде. Для текущей версии upstream: `uv tool install -p 3.13
  serena-agent==2.1.0`, затем `serena init`. uv подготавливает отдельный
  интерпретатор инструмента. В хосте задайте stdio-команду `serena
  start-mcp-server --project <Repo>`. После подключения прочитайте инструкции
  сервера, выберите правильный проект и успешно прочитайте реальный Python-символ.
  [Установка](https://oraios.github.io/serena/02-usage/010_installation.html),
  [запуск](https://oraios.github.io/serena/02-usage/020_running.html).
  Существующую работающую установку сначала проверяйте, не заменяйте автоматически.
- **PF MCP.** Полезен для потребительских проектов PF; для редактирования исходников
  не обязателен. В Codex проверьте план командой `<PfPython> <Core>/bin/pf.py
  codex-mcp install --workplace <Workplace> --distribution-root <Core> --python
  <PfPython>`, затем примените настройку с `--apply`. Проверьте `codex-mcp status`,
  перезагрузите настоящий хост и убедитесь в доступности инструментов PF и
  `pf.actions.list`. [Порядок подключения](../../getting-started/runtime-autostart.md#codex-mcp-registration).
- **Playwright MCP.** Подготовьте для проверок браузера, интерфейса и HTML-документации.
  Нужна поддерживаемая Node.js LTS. Установите `npm install --prefix
  <Tools>/browser-mcp --save-exact @playwright/mcp@0.0.85`, затем браузер:
  `node <Tools>/browser-mcp/node_modules/playwright/cli.js install chromium`.
  В хосте задайте команду `node` и аргументы
  `<Tools>/browser-mcp/node_modules/@playwright/mcp/cli.js --config
  <Tools>/browser-mcp/pf-browser.json`; содержимое локального JSON приведено ниже.
  Проверьте открытие локальной тестовой страницы и чтение
  её структуры. На Linux установите системные зависимости браузера по
  [официальной инструкции](https://github.com/microsoft/playwright-mcp).
- **Context7.** Дополнительный источник после локальной документации. Подключите
  HTTP MCP `https://mcp.context7.com/mcp`. Если используется API key, передавайте
  его из локального хранилища секретов/окружения в Authorization, не сохраняйте
  значение в репозитории. Проверьте разрешение библиотеки и один запрос
  документации. [Настройка хостов](https://context7.com/docs/resources/all-clients).
- **Chrome/Firefox DevTools.** Дополнительные средства диагностики при конкретной
  необходимости. Для браузерных проверок сначала используется Playwright.

Сохраните локальный файл Playwright `<Tools>/browser-mcp/pf-browser.json`:

```json
{
  "browser": {
    "browserName": "chromium",
    "isolated": true,
    "launchOptions": { "headless": true }
  }
}
```

Если uv отсутствует, установите его по
[официальной инструкции](https://docs.astral.sh/uv/getting-started/installation/).
Версии Serena и Playwright выше сверены с upstream при подготовке этого документа.
Новые версии проверяйте перед заменой принятой конфигурации и фиксируйте
фактически установленную версию.

После успешного подключения внесите нужные capabilities в PF через
`mcp-register` с реальным transport и командой без секретов. Наличие записи
конфигурации или запущенного процесса не доказывает, что хост подключён к MCP.
Runtime, App Server, автозапуск, Director, hooks и Ledger — отдельные возможности
продукта. Эта подготовка не устанавливает службы. PHP, Joomla и маркетинговые
пакеты не входят в зависимости разработки PF Core.

## 6. Обновления и подтверждение готовности

В каждом `package.yaml` объявлен `update_sites` с адресом
`releases/latest/download/<manifest>.json` собственного репозитория. ZIP каждой
версии имеет отдельный URL и SHA-256. Последующие обновления выполняются штатно:

```sh
<PfPython> <Core>/bin/pf.py update entity-sources rebuild --workplace <Workplace>
<PfPython> <Core>/bin/pf.py update candidates refresh --workplace <Workplace>
<PfPython> <Core>/bin/pf.py update candidates list --workplace <Workplace>
<PfPython> <Core>/bin/pf.py update stage --workplace <Workplace> --candidate <id>
<PfPython> <Core>/bin/pf.py update verify --workplace <Workplace> --candidate <id>
<PfPython> <Core>/bin/pf.py update apply --workplace <Workplace> --candidate <id> --confirm
```

Перед применением прочитайте changelog и проверьте целевой каталог. Сохраните
резервную копию; после применения проверьте пакет. У проверенной ревизии Core
`8ebacb61` команда `update rollback` восстанавливает файлы, но оставляет новую
версию в реестре установленных сущностей. После такого отката сопоставьте версии
и согласуйте точную запись реестра перед очередным поиском обновлений. Для новой
версии Core отдельно проверьте, исправлено ли это ограничение.

Перед сообщением «устройство готово» сохраните приватный отчёт: ревизии исходников
и Core, версии Python и инструментов, версии/хеши пакетов, фактические каталоги,
результаты doctor, реальные подключения MCP и недоступные возможности. Выполните
проверки схем, checksums и public-cleanliness из CONTRIBUTING, подходящий
существующий smoke и необходимые проверки изменённого кода. Для применимых
исполняемых изменений нужны реальные Windows и Linux, включая CI; пропуск или
отсутствие среды не считается успешной проверкой. Доставка изменений: рабочая
ветка → PR в `dev` → review и проверки → разрешённое слияние → проверенное зеркало
GitVerse.
