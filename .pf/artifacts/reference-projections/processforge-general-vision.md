# ProcessForge: reference projection of the general vision

Status: reference; source-verified

Recorded: 2026-09-23

Scope: preserve the operator's wording of the general ProcessForge vision and
the accompanying codebase-conformance assessment. This is a manually authored
conceptual reference projection, not a generated Runtime projection.

Source basis: operator-provided ChatGPT Web text; current source tree at
`a180ad624442d4fbe8ac1710073ef7d4c44babc4` (ProcessForge 1.1.0).

## Operator reference — verbatim

Да, и это как раз тот случай, где полезно зафиксировать несколько **неизменных опор**, чтобы дальше нас снова не уносило то в «оркестратор», то в «skills-фреймворк», то в «обвязку Codex».

Для себя я бы теперь держал PF так:

* **PF не принадлежит ни одной экосистеме моделей.**
* **PF хранит внешнее состояние процесса и проекта**, чтобы его не приходилось держать в памяти конкретной модели.
* **PF вычисляет рабочий контекст**, сужая и обогащая его знаниями, инструментами, шаблонами и состоянием текущей стадии.
* **Модели — сменные исполнители**, а не архитектурный центр системы.
* **Служебная бухгалтерия должна по максимуму уходить из промпта и поведения агента** в хуки, Python, MCP, журнал, телеметрию, блокировки и адаптеры.
* **Профильные и локальные модели — такие же полноценные участники**, как GPT/Claude/Gemini.
* **Глубокие интеграции с конкретной экосистемой допустимы только как адаптеры**, а не как зависимость ядра.

И ещё одна формула, которая, по-моему, хорошо держит весь проект в фокусе:

> **PF хранит то, что исполнитель не должен помнить сам, и выдаёт ему то, что нужно знать для текущей работы.**

Это хорошо связывает и самый ранний файловый поток, и процессы, и знания, и журнал вахтёра, и мультимодельность, и будущую локальную фильтрацию чувствительных данных.

А наше постоянное «качание» раньше возникало потому, что мы обсуждали очередной конкретный механизм — skills, MCP, Codex, оркестрацию, память — и начинали невольно принимать этот механизм за центр всей системы. Теперь правильнее каждый раз проверять новую идею вопросом:

> **Это часть ядра PF или всего лишь один из способов подключения исполнителя/ресурса?**

Это должно сильно уменьшить архитектурный дрейф в следующих обсуждениях.

## Codebase-conformance assessment

### Confirmed current contracts

- PF is provider-neutral and platform-neutral at the Core boundary. `README.md`
  and `docs/concepts/domain-neutral-core.md` describe versioned processes,
  resources, templates, drivers, and platform contracts rather than a
  model-specific kernel.
- `.pf/` and the Workplace layer persist the project and process facts that
  must outlive an executor: context snapshots, selected resources, runs,
  assignments, evidence, reviews, handoffs, events, and private runtime state.
- `ProjectContextService` resolves bounded project context, and
  `ProcessExecutionService` pins a process, snapshot, resources, and
  specialization set into the Run and assignment capsule. `pf.work.state`
  exposes current-stage inputs, artifacts, gates, obligations, blockers, and
  allowed outcomes.
- Process definitions are data; the normal execution path does not require a
  provider-specific model. Runtime drivers are optional; `manual` is the
  default and `generic-shell` is a generic executor seam.
- Hooks, Runtime, Agent Ledger, raw ingress, event records, locks, projections,
  and MCP move technical lifecycle accounting outside an agent's prompt.
  Codex hooks and the stdio MCP facade are optional host integrations over the
  shared Core.
- Sensitive data already has local/private handling boundaries: private raw
  event storage, redacted chat records, secret/path filtering, and
  metadata-only export. A distinct comprehensive local-filtering product layer
  is not yet a separately implemented capability.

### Required precision

1. PF does not build one universal complete prompt. It resolves and pins a
   fresh, authorization-bounded snapshot and returns the current work contract.
   Stage-specific re-resolution of the entire resource universe remains a
   stated future refinement.
2. Semantic review and truthful evidence cannot be entirely delegated to the
   machinery. File existence, hashes, and gate attestations are verified, but
   PF intentionally does not treat them as proof that an artifact was
   semantically reviewed.
3. Local, Claude, Gemini, and other model ecosystems are not yet symmetric
   out-of-the-box integrations. They can participate through `generic-shell`
   or an added driver, while `codex-exec` is presently the supplied
   model-specific driver. The model-neutral claim is architectural; identical
   operational support is future extension work.
4. The Core deliberately does not depend on Codex, but the optional
   project-initialization facade has a named `install_codex_hooks` repair
   action. It remains optional host telemetry, not a required project feature.

## Durable architectural test

Use the following classification when evaluating a proposal:

- **Core invariant:** file-first state, context snapshot and pinning, process
  lifecycle, evidence/gates, identities, containment, and durable event rules.
- **First-class extension data:** process definitions, knowledge packages,
  templates, skills, tool/MCP registrations, platform contracts, and drivers.
  These are important inputs, but their concrete domain/provider content is
  not the kernel.
- **Adapter or transport:** Codex hooks, MCP stdio transport, a particular
  model CLI/SDK, and a concrete runtime driver.

Orchestration is therefore not the product's centre of gravity: its generic
coordination contracts are Core mechanics, while a chosen multi-agent plan and
its workers are an optional execution arrangement.

## Preferred concise formulation

> PF хранит проверяемое состояние процесса, которое не должно жить только в
> памяти исполнителя, и по свежему snapshot выдаёт исполнителю ограниченный
> контракт текущей работы.

This formulation preserves the operator's intent while avoiding a claim that
PF knows every fact an executor may need for reasoning or produces a complete
prompt automatically.

## Verification sources

- `README.md`
- `docs/concepts/domain-neutral-core.md`
- `docs/concepts/garage-core.md`
- `docs/concepts/declarative-process-execution.md`
- `docs/concepts/runtime-drivers.md`
- `docs/concepts/runtime-mcp.md`
- `docs/concepts/context-capsule.md`
- `docs/concepts/hooks-events.md`
- `docs/concepts/chat-relay.md`
- `src/processforge_core/garage.py`
- `src/processforge_core/process_execution.py`
- `src/processforge_core/project_initialization.py`
- `tools/pf_runtime/raw_ingress_kernel.py`
