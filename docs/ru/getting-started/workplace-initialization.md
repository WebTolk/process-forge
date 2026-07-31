# Инициализация workplace

Workplace — машинный слой ProcessForge. Он хранит общие ресурсы, которые могут
использовать разные проекты: шаблоны, пакеты знаний, platform contracts и
реестры.

В полностью автоматическом режиме процесс начинается с необязательной стадии
исследования устройства. Агент только читает доступные `AGENTS.md`, навыки,
локальную документацию, платформы, цепочки инструментов, инструменты, настройки
MCP и корни проектов. Затем он объясняет, что где лежит и какую роль имеет, и
предлагает, какие сущности ProcessForge нужно создать или зарегистрировать.

Команду можно запускать из любой папки. Не используйте текущую рабочую папку
как неявный project root. Настройка машины должна явно фиксировать роли:
установленный дистрибутив ProcessForge, workplace root, необязательный global
agent root, knowledge roots и candidate project roots.

Создайте workplace из корня дистрибутива:

```bash
python bin/pf.py workplace-init --workplace ../pf-workplace --apply
python bin/pf.py doctor-workplace --root ../pf-workplace
```

Профиль `generic` оставляет все предметные официальные packs неактивными:

```bash
python bin/pf.py workplace-init --profile generic --workplace ../pf-workplace --apply
```

Если workplace должен сразу получить готовый предметный процесс, выберите
соответствующий профиль:

```bash
python bin/pf.py workplace-init --profile software-development --workplace ../pf-workplace --apply
python bin/pf.py workplace-init --profile content-workflow --workplace ../pf-workplace --apply
python bin/pf.py workplace-init --profile verification --workplace ../pf-workplace --apply
```

Профиль активирует пакет данных, а не меняет ядро ProcessForge. Обнаружение и
явная активация описаны в разделе [Официальные packs](official-packs.md).

Не создавайте `.pf/` внутри проекта на этом шаге. Проект подключается отдельно
через `project-onboard`.

Применение автоматической настройки начинается только после подтверждения
предложения. Если у агента нет прав на широкий просмотр дисков, он использует
ограниченную область: глобальный `AGENTS.md` и настроенные корни навыков,
документации, платформ, цепочек инструментов и проектов.

После инициализации сохраните путь к workplace в инструкции для агентов или в
локальной документации команды.

## Coordination mode

Workplace хранит capability, а не обязательный режим всех проектов:

```yaml
coordination:
  director_enabled: true
  director_office_enabled: true
  default_project_mode: simple
```

Даже если Director capability включена, отдельный проект может оставаться
`simple`. Для смешанной работы обычно удобно держать
`default_project_mode: simple`, а сложные проекты переводить в `organized`
локально.

```bash
python bin/pf.py workplace-mode status --workplace ../pf-workplace
python bin/pf.py workplace-mode set --workplace ../pf-workplace --director-enabled true --director-office-enabled true
python bin/pf.py workplace-mode set-default-project-mode --workplace ../pf-workplace --mode simple
python bin/pf.py workplace-mode doctor --workplace ../pf-workplace
```
## Порядок Создания Ресурсов

После `workplace-init` создавайте ресурсы в таком порядке, когда они нужны:
knowledge packages, tools/MCP, templates, platform contracts, затем
specializations. Specializations ссылаются на уже существующие resource ids и
хранятся в workplace или project flow, а не в ProcessForge distribution root.
