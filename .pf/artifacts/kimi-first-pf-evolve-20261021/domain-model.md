# Domain Model

## Entities
| Entity | Responsibility |
|---|---|
| NewAgentOnboarding | Фиксирует первый опыт и проблемы адаптации |
| UsabilityFinding | Классифицирует проблему: technical / hard / unclear / inconvenient / redundant |
| ImprovementAction | Рекомендация по устранению проблемы |

## Relationships
- Onboarding contains Findings
- Finding maps to ImprovementAction
