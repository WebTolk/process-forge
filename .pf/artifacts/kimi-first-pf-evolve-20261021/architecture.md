# Architecture

## Onboarding feedback architecture

```
New agent session
  -> Observe friction points
  -> Classify findings (technical / hard / unclear / inconvenient / redundant)
  -> Map to improvement actions
  -> Record evolve report
```

## Components
- Observation collector: анализ текущей сессии.
- Finding classifier: категоризация проблем.
- Improvement mapper: приоритизация и рекомендации.
- Evolve recorder: запись в стандартном формате PF.

## Boundaries
- No code changes in this Work.
- Feedback only; fixes are future Work.
