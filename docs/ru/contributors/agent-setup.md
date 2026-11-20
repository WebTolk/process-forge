# Подготовка агента к разработке PF на новом устройстве

[English](../../contributors/agent-setup.md)

Эта инструкция предназначена для агента, которому поручено после клонирования
ProcessForge подготовить рабочее место с общими знаниями, инструментами и MCP.
Сначала прочитайте корневые [AGENTS.md](../../../AGENTS.md) и
[CONTRIBUTING.ru.md](../../../CONTRIBUTING.ru.md).

Рабочее место PF создаётся отдельно от исходников. Чтение инструкций и первичная
подготовка допускаются до Work. Затем содержательная разработка ведётся через
собственные локальные контекст и Work PF. Создайте игнорируемое проектное состояние,
не восстанавливая чужую `.pf` и историю другого устройства.

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

Для этого сценария используйте отдельный Core из зафиксированного `origin/dev`
либо релиз, явно проверенный на те же возможности. Установка опубликованных знаний
проверена на исходной ревизии `d0d18f7d`; старый Core 1.2.0 отклоняет внешнюю ссылку
JSON Schema при doctor пакета и для этой подготовки не подтверждён. Инструкции
из `main` направляют разработку в рабочую ветку от `dev`, не обновляя стабильный
Runtime. Создайте клон точной ревизии: `git clone --no-hardlinks <Repo> <Core>`, затем
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
<PfPython> <Core>/bin/pf.py workplace-init --workplace <Workplace> --profile software-development --dry-run
<PfPython> <Core>/bin/pf.py workplace-init --workplace <Workplace> --profile software-development --apply
<PfPython> <Core>/bin/pf.py doctor-workplace --root <Workplace>
```

Профиль `software-development` выбирает поставляемые процессы разработки.
Выберите процесс под задачу; он дополняет правила участия и доставки изменений.
Python-пакеты знаний ниже устанавливаются отдельно. Для существующего workplace
сначала проверьте состояние и активные пакеты; повторная инициализация не является
способом его обновления.

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

Для разработки **самого ProcessForge** выберите эти пакеты в требованиях
локального контекста проекта по стабильным ID и ресурсу `root`, затем обновите
и проверьте контекст. Сначала читайте индекс пакета, затем нужные документы.
Архитектуру PF читайте в `docs/` текущей ревизии и вложенных `AGENTS.md`.
Нативный поиск и доступ Work используют действующий снимок проекта и разрешённую
выборку; установка пакета в workplace сама по себе не выбирает его для проекта.

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
- **PF MCP.** Необязательный транспорт для обязательного локального процесса PF;
  допустим и штатный CLI. В Codex проверьте план командой `<PfPython> <Core>/bin/pf.py
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

## 6. Инициализировать локальный проект PF и выбрать источник задач

Если `.pf` уже существует, сначала проверьте её и сохраните корректную локальную
историю; продолжайте существующую Work по точным идентификаторам. Для свежего клона
выберите процесс под задачу из активного пакета разработки, например
`software-feature-development` или `bug-fix`. Просмотрите план, затем примените:

```sh
<PfPython> <Core>/bin/pf.py project-onboard --project-root <Repo> --workplace <Workplace> --type processforge-development --process <process-id> --coordination-mode simple --dry-run
<PfPython> <Core>/bin/pf.py project-onboard --project-root <Repo> --workplace <Workplace> --type processforge-development --process <process-id> --coordination-mode simple --apply
<PfPython> <Core>/bin/pf.py doctor-project --project-root <Repo>
<PfPython> <Core>/bin/pf.py project-context-check --project-root <Repo>
```

Тип `processforge-development` отличает исходный проект от ошибочного подключения
установленного Core. `simple` — начальный режим координации; более сложный режим
выбирается вместе с необходимыми ему службами. Прочитайте план onboarding.
Генерация входа сохраняет общий текст, но может дописать управляемый блок в корневой
AGENTS: проверьте локальный diff и не включайте такой побочный результат настройки
в посторонний PR. Не используйте `--force` для обхода конфликта входа. Ошибки
контекста и doctor нужно устранить до содержательной Work.

Перенесите значения [профиля совместной работы](../../contributors/collaboration-profile.json)
в дополнительные поля `project.collaboration`, сохранив локальную идентичность
проекта. Для 1.3.0 по умолчанию используется `local_pf`. Прочитайте
[обе схемы и поля ссылок](task-collaboration.md). В режиме `github` issue читается
или создаётся до связанной Work. В режиме `local_pf` его можно создать позже,
при публикации крупной задачи или существенного результата.

Выберите ID необходимых знаний и фактические capabilities инструментов/MCP в
локальных требованиях контекста. После намеренного изменения конфигурации выполните
`project-context-refresh` и `project-context-check`. Для нативного поиска используйте
`search-index refresh` и `search-index doctor` с явными путями проекта/workplace.
Прочитайте `pf.context`, создайте или продолжите точную Work, прочитайте её
assignment/капсулу и дополнительные ссылки, выполняйте выбранный процесс через
`pf.work.state` / `pf.work.transition`. Для CLI смотрите help/schema установленного
действия; не придумывайте новые аргументы `pf.work.start` для дополнительных полей.
Корневой `.pf` остаётся игнорируемым и приватным. Чистая копия для проверки исходников
может оставаться без `.pf`; контрибьютер создаёт своё состояние после клонирования.

## 7. Обновления и подтверждение готовности

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
резервную копию; после применения проверьте пакет. Обновление сохраняет прежнюю
запись выбранного subject рядом с резервной копией файлов. `update rollback`
восстанавливает её, включая прежнее отсутствие, сохраняя остальные записи реестра.
При конфликте текущих метаданных или старой резервной копии без сохранённой записи
команда отказывает: сохраните эти данные для явного восстановления. Неуспешная
операция с файлами или метаданными не означает завершённый откат. Сохраните receipt
и повторяйте только поддерживаемый защищённый путь. Перед новым поиском обновлений
проверьте версии и в файлах, и в реестре.

Перед сообщением «устройство готово» сохраните приватный отчёт: ревизии исходников
и Core, версии Python и инструментов, версии/хеши пакетов, фактические каталоги,
результаты doctor, реальные подключения MCP и недоступные возможности. Выполните
проверки схем, checksums и public-cleanliness из CONTRIBUTING, подходящий
существующий smoke и необходимые проверки изменённого кода. Для применимых
исполняемых изменений нужны реальные Windows и Linux, включая CI; пропуск или
отсутствие среды не считается успешной проверкой. Доставка изменений: рабочая
ветка → PR в `dev` → review и проверки → разрешённое слияние → проверенное зеркало
GitVerse.
