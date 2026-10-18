# Audit hooks report

Статус: завершён bounded audit. Product-код не изменялся; production Runtime не запускался и не перезапускался.

Проверены: `host.py`, `service.py`, `codex_hooks.py`, `raw_ingress_kernel.py`, `codex_integration.py`, hook dispatch в `processforge.py`.

## Сводка

| ID | Severity | Дефект | Статус |
|---|---|---|---|
| H-01 | High | Повторная доставка повторно dispatch-ит hooks | подтверждено |
| H-02 | High | `runtime serve` захватывает workplace при живом orphaned Runtime | подтверждено |
| H-03 | High | Ошибка чтения project cache навсегда убивает scheduler thread | подтверждено |
| H-04 | Medium | `SessionStart` startup/resume имеют одинаковый event id | подтверждено |

## H-01 — повторный hook dispatch для уже существующего события

Файлы и строки:

- `tools/processforge.py:11255-11274`
- `tools/processforge.py:11398-11415`
- `tools/pf_runtime/host.py:925-959`

Контракт: существующее событие должно быть deduplicated; deterministic derived key используется для идемпотентного эффекта conversation capture.

Триггер: Codex hook доставлен повторно после успешной первой записи. На втором проходе `append_chat_message()` находит существующий `message_id`, но повторно вызывает `emit_process_event()`. `append_process_event()` видит существующий event id, однако всё равно выполняет `dispatch_hooks()`.

Ожидается: одна запись события и одна hook delivery.

Фактически: запись события остаётся одна, но создаётся новая `delivery_id`, повторно обновляется outbox-файл и добавляется новый result-файл.

Изолированный reproducer:

```python
import sys
sys.path.insert(0, "tools")
import processforge as pf

class H:
    def __init__(self, f): self.f = f
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def write(self, text): self.f.data += text

class F:
    def __init__(self): self.data = ""; self.parent = self
    def mkdir(self, **kw): pass
    def is_file(self): return bool(self.data)
    def read_text(self, **kw): return self.data
    def open(self, *a, **kw): return H(self)

events = F()
calls = []
pf.event_runtime_paths = lambda _: (events, F())
pf.dispatch_hooks = lambda *a, **kw: calls.append(1)

event = {"event_id": "evt_same", "event_type": "chat.message.recorded"}
pf.append_process_event(None, event)
pf.append_process_event(None, event)

print("event_lines=", len(events.data.splitlines()), "dispatch_calls=", len(calls))
```

Вывод:

```text
event_lines= 1 dispatch_calls= 2
```

Воздействие: повторные outbox delivery могут быть обработаны downstream как новые попытки; result-журнал разрастается, а timestamps/outbox mtime меняются при каждой повторной доставке.

Минимальное исправление: выполнять `dispatch_hooks()` только если событие было реально добавлено, либо вынести повторную delivery в отдельную явно идемпотентную операцию.

Изолированная remediation-задача:

- Разрешённые файлы: `tools/processforge.py`, `tools/pf_runtime/host.py`, профильный smoke-тест.
- Acceptance: повторный `append_process_event()` даёт одну journal-запись и одну hook delivery; повторный Codex capture не создаёт новую delivery.
- Сложность: S.
- Рекомендуемая junior-модель: `gpt-5.3-codex-spark`.

## H-02 — takeover orphaned Runtime

Файлы и строки:

- `tools/pf_runtime/service.py:181-209`
- `tools/pf_runtime/service.py:255-269`
- `tools/pf_runtime/service.py:481-511`

Контракт: `inspect_lifecycle()` явно считает `orphaned` небезопасным состоянием и отмечает, что запуск второго daemon создаст двух владельцев workplace.

Триггер: lock существует, но lock/state не совпадают, при этом старый PID ещё жив. Это возможно также в коротком окне между созданием lock и записью `service.json`.

Ожидается: `acquire_singleton()` отклоняет запуск и требует recovery.

Фактически: `acquire_singleton()` отклоняет только `ready`, `starting`, `stopping`, `failed`; для `orphaned` удаляет существующий lock и получает новый.

Изолированный reproducer:

```python
from tools.pf_runtime import service

class P:
    def __init__(self):
        self.parent = self
        self.unlinked = False
    def mkdir(self, **kw): pass
    def unlink(self, **kw): self.unlinked = True

class H:
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def write(self, text): pass

class C:
    def now_utc(self): return "now"

p = P()
calls = []
service.runtime_root = lambda _: p
service.lock_path = lambda _: p
service.cleanup_stale_runtime = lambda *_: None
service.inspect_lifecycle = lambda *_: {"kind": "orphaned", "pid": 123}
def fake_open(*a, **kw):
    calls.append(1)
    if len(calls) == 1:
        raise FileExistsError
    return 7
service.os.open = fake_open
service.os.fdopen = lambda *a, **kw: H()

service.acquire_singleton(p, C(), "new-instance")
print("open_calls=", len(calls),
      "lock_unlinked=", p.unlinked,
      "result=second_owner_acquired")
```

Вывод:

```text
open_calls= 2 lock_unlinked= True result=second_owner_acquired
```

Воздействие: два Runtime могут одновременно принимать события, писать state и scheduler-результаты одного workplace. Это может привести к потерянным или перемешанным lifecycle-эффектам.

Минимальное исправление: считать `orphaned` блокирующим состоянием в `acquire_singleton()`; разрешать takeover только отдельной explicit recovery процедурой после проверки PID/instance.

Изолированная remediation-задача:

- Разрешённые файлы: `tools/pf_runtime/service.py`, lifecycle smoke-тест.
- Acceptance: `runtime serve` не захватывает orphaned lock; stale lock с мёртвым PID восстанавливается только через предусмотренный recovery path; конкурентный старт оставляет одного владельца.
- Сложность: M.
- Рекомендуемая junior-модель: `gpt-5.3-codex-spark`.

## H-03 — scheduler thread умирает до блока обработки ошибок

Файлы и строки:

- `tools/pf_runtime/service.py:293-302`
- `tools/pf_runtime/service.py:349-373`
- `tools/pf_runtime/host.py:1272-1297`

Контракт: комментарий scheduler прямо требует деградации, а не падения Runtime из-за одного плохого проекта.

Триггер: `known_project_roots()` выбрасывает исключение, например при повреждённом host state. Вызов находится до `try` в `scheduler_loop()`.

Ожидается: ошибка фиксируется в `last_scheduler_error`, Runtime остаётся жив, следующий tick продолжает работу.

Фактически: исключение выходит из thread; `save()` не вызывается, `health` не меняется, scheduler больше не выполняет ticks.

Изолированный reproducer:

```python
import threading
from tools.pf_runtime import service

class E:
    def __init__(self): self.n = 0
    def wait(self, _):
        self.n += 1
        return self.n > 1

class R:
    interval = 0
    stop_event = E()
    state = {}
    state_lock = threading.RLock()
    def known_project_roots(self):
        raise RuntimeError("corrupt host state")
    def save(self):
        print("save-called")

r = R()
try:
    service.RuntimeProcess.scheduler_loop(r)
except Exception as exc:
    print(type(exc).__name__, str(exc))
print("state=", r.state)
```

Вывод:

```text
RuntimeError corrupt host state
state= {}
```

Воздействие: Runtime продолжает выглядеть запущенным, но Ledger maintenance, Director, Inspector и projection scheduler фактически остановлены.

Минимальное исправление: включить получение `roots` в `try`; дополнительно изолировать обработку проектов внутри `host.tick_payload()`, чтобы один повреждённый проект не блокировал остальные.

Изолированная remediation-задача:

- Разрешённые файлы: `tools/pf_runtime/service.py`, `tools/pf_runtime/host.py`, scheduler smoke-тест.
- Acceptance: исключение при чтении одного проекта не убивает thread; `last_scheduler_error` и operator log заполняются; здоровые проекты продолжают tick.
- Сложность: M.
- Рекомендуемая junior-модель: `gpt-5.3-codex-spark`.

## H-04 — collision event id для SessionStart startup/resume

Файлы и строки:

- `tools/pf_runtime/codex_hooks.py:48-71`
- `tools/pf_runtime/host.py:350-363`
- `tools/pf_runtime/host.py:591-600`

Контракт: разные normalized lifecycle facts должны сохраняться как разные project events. `startup` и `resume` маппятся в разные event types.

Триггер: один и тот же Codex `session_id` получает `SessionStart` с `source=startup`, затем `source=resume`.

Ожидается: два события: `agent.session.started` и `agent.session.resumed`.

Фактически: `source` не входит в `event_id`; Host считает второе событие duplicate и не вызывает Ledger effect для resume.

Изолированный reproducer:

```python
from tools.pf_runtime.codex_hooks import normalized_event

startup = normalized_event({
    "hook_event_name": "SessionStart",
    "source": "startup",
    "cwd": "C:/project",
    "session_id": "session-1",
})
resume = normalized_event({
    "hook_event_name": "SessionStart",
    "source": "resume",
    "cwd": "C:/project",
    "session_id": "session-1",
})

print(startup["event_id"])
print(resume["event_id"])
print("same_id=", startup["event_id"] == resume["event_id"])
print("types=", startup["event_type"], resume["event_type"])
```

Вывод:

```text
codex:SessionStart:session-1::
codex:SessionStart:session-1::
same_id= True
types= agent.session.started agent.session.resumed
```

Воздействие: resume/clear/compact lifecycle-факты могут теряться из project journal и Ledger projection.

Минимальное исправление: включить normalized source в состав event id либо использовать отдельный deterministic identity basis, содержащий `hook`, `source`, session и provider identifiers.

Изолированная remediation-задача:

- Разрешённые файлы: `tools/pf_runtime/codex_hooks.py`, ingress smoke-тест.
- Acceptance: startup/resume/clear с одной сессией получают разные event ids; повтор одинакового payload остаётся deduplicated.
- Сложность: S.
- Рекомендуемая junior-модель: `gpt-5.3-codex-spark`.

## Проверки и ограничения

Чистые reproducer’ы H-01—H-04 выполнены. Write-heavy smoke-тесты raw ingress/Codex integration не прошли из-за sandbox `PermissionError` при создании временных каталогов; это ограничение окружения, а не диагностированный дефект product-кода. Production Runtime и внешние сервисы не затрагивались.