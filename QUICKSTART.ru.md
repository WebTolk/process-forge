# Prompts быстрого старта ProcessForge

Этот quickstart написан для человека. Скопируйте нужный prompt в ИИ-агента.
Полный набор команд агент должен брать из
[docs/ru/getting-started/agent-prompts.md](docs/ru/getting-started/agent-prompts.md).

## 1. Подготовить инструмент

```text
Подготовь ProcessForge на этой машине.

Найди checkout или распакованный дистрибутив ProcessForge, изучи документацию и
используй docs/ru/getting-started/agent-prompts.md как операционный command
runbook.

Проверь, что distribution root пригоден к работе, и назови точный путь, который
нужно использовать как <processforge-root>.
```

## 2. Инициализировать workplace

```text
Инициализируй ProcessForge workplace.

Используй агентский command runbook ProcessForge. Создай workplace по указанному
мной пути или предложи понятный локальный путь. Запусти doctor-workplace,
исправь структурные проблемы, которые можно безопасно исправить, и сообщи
результат.
```

## 3. Подключить проект

```text
Подключи этот репозиторий к ProcessForge.

Сначала изучи структуру репозитория, выбери консервативный project type,
подключи его к существующему workplace, прочитай созданный
.pf/START_AGENT_HERE.md, запусти doctor-project и кратко опиши, что теперь
ProcessForge знает о проекте.
```

## 4. Начать run

```text
Создай ProcessForge run для моего текущего запроса.

Используй task-batch execution. Разбей работу на tasks, фиксируй iterations по
ходу работы, записывай artifacts/reviews/handoffs там, где этого требует
процесс, и заверши run-summary и run-doctor.
```

## 5. Создать собственный процесс

```text
Создай новый ProcessForge process.

Используй process authoring flow, а не ручное написание YAML первым шагом.
Спроси цель процесса, stages, roles, gates, artifacts, нужные знания и ожидаемый
task loop. Проверь draft, примени его и проверь итоговый process.
```

## 6. Создать общие resources

```text
Создай общие ProcessForge resources для этого проекта.

Спроси, нужны ли reusable templates, knowledge packages, platform contracts или
всё сразу. Общие resources держи в workplace, ссылайся на них по id и запускай
соответствующие doctor-проверки.
```

## 7. Использовать subagents

```text
Спланируй ProcessForge-assisted multi-agent run.

Тесно связанную работу оставь в main agent. Subagents используй только для
независимых scopes, каждому дай непересекающуюся зону ответственности, требуй
file-based evidence и сверяй их результаты в текущем run перед финальной
доставкой.
```

## 8. Проверить перед delivery

```text
Проверь репозиторий перед delivery.

Используй ProcessForge release и validation runbook для агентов. Запусти нужные
проверки, пересобери release archive с нейтральным именем, проверь архив и
сообщи точные pass/fail evidence перед commit или push.
```
