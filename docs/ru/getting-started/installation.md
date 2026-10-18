# Установка

Установите ProcessForge один раз как Python-инструмент, затем создайте рабочее
место (workplace) и подключайте проекты. Сначала прочитайте
[требования](../requirements.md): библиотеки, SQLite, доверенные сертификаты,
права доступа и планирование памяти.

## Получите дистрибутив

Распакуйте официальный архив релиза в отдельный каталог. Для установки из
исходников клонируйте репозиторий:

```bash
git clone <processforge-repo> process-forge
cd process-forge
```

Для установки из архива Git не нужен. Храните изменяемые workplace, проекты и
Python-окружение отдельно от заменяемого дистрибутива. В примерах используются
соседние каталоги `../pf-venv`, `../pf-workplace` и `../my-project`.

## Создайте изолированное Python-окружение

В Linux/macOS из корня дистрибутива:

```bash
python3 -m venv ../pf-venv
source ../pf-venv/bin/activate
python -m pip install -r requirements.txt
python bin/pf.py version
```

В Windows PowerShell:

```powershell
py -3 -m venv ../pf-venv
../pf-venv/Scripts/python.exe -m pip install -r requirements.txt
../pf-venv/Scripts/python.exe bin/pf.py version
```

До создания окружения выберите нужную установленную версию Python. Если `venv`
или `pip` отсутствует, установите соответствующий компонент по инструкции
Python для своей ОС. Запускайте `python -m pip` из этого окружения, чтобы
PyYAML установился для того же интерпретатора, которым будет работать PF.

Далее `python` обозначает интерпретатор этого окружения. В Windows его можно
вызывать напрямую как `../pf-venv/Scripts/python.exe`, без активации сценариев
PowerShell и изменения политики их исполнения. При переходе в другую папку
скорректируйте путь или укажите полный. Если подключаете Runtime или MCP,
регистрация должна использовать интерпретатор с теми же зависимостями;
его можно явно закрепить через `--python`.

## Проверьте среду до создания состояния

Выполните [предварительную проверку без записи](../requirements.md#предварительная-проверка-без-записи), затем:

```bash
python bin/pf.py version
python bin/pf.py --help
```

Эти команды не устанавливают службы и не создают workplace. Для первой
настройки с участием человека перейдите к
[пошаговой настройке workplace](guided-workplace-setup.md): агент собирает
ответы и использует существующие файловые команды настройки.

Если пути и ресурсы уже определены, автоматическую настройку для разработки
ПО начните с предварительного плана workplace, проверьте его и примените:

```bash
python bin/pf.py workplace-init --workplace ../pf-workplace --profile software-development --dry-run
python bin/pf.py workplace-init --workplace ../pf-workplace --profile software-development --apply
python bin/pf.py doctor-workplace --root ../pf-workplace
```

Подготовьте нужные общие ресурсы до подключения проекта. Для предварительного
просмотра каталог проекта уже должен существовать; применение также может
создать новый корень проекта:

```bash
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --dry-run
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --apply
python bin/pf.py agent-start-prompt --project-root ../my-project
```

Сокращённая команда `first-run` не принимает `--profile`. Чтобы выбрать
встроенный профиль workplace, используйте две команды выше. См.
[первый запуск](first-run.md) и [порядок инициализации](initialization-order.md).

## Работа в подключённом проекте

После подключения используйте проектный launcher из корня проекта:

```bash
cd ../my-project
python .pf/runtime/bin/pf.py doctor-project --project-root .
python .pf/runtime/bin/pf.py project-context-check --project-root .
```

Команда `python bin/pf.py` выполняется из дистрибутива, а не из обычного проекта.
Не копируйте весь репозиторий в `.codex`, `.claude`, `.agents` и другие папки
настроек агентов. Вход начинается с корневого `AGENTS.md`; для старого проекта
без него явно используется `.pf/AGENTS.md`. Выберите загрузчик или адаптер по
[политике входа](../concepts/agent-entry.md).

Garage не требует PF Runtime, MCP или хуков Codex. Подключайте их, когда
оператор выбрал соответствующий сценарий. Агент обычного проекта не должен
устанавливать, запускать, перезапускать или чинить инфраструктуру. См.
[запуск Runtime и MCP](runtime-autostart.md).

## Проверки разработки и релиза

Эти расширенные проверки нужны для исходников или подготовленного релиза.
Они запускают дочерние процессы, требуют записи отчётов и временных данных,
а некоторые проверки разработки и релиза — Git:

```bash
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-test --root .
python bin/pf.py release-test --root . --trace-smokes
```

`--trace-smokes` записывает `.pf/runtime/release-test/latest-trace.ndjson`:
имя текущего smoke, прошедшее время, бюджет таймаута и причину его превышения.
Изменённые исходники могут отличаться от опубликованного списка контрольных
сумм. Эта проверка не заменяет валидацию контекста и капсул.

## UTF-8 в Windows PowerShell

Если русский текст отображается неверно, настройте кодировку консоли.
Сами файлы остаются в UTF-8:

```powershell
chcp 65001
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
```
