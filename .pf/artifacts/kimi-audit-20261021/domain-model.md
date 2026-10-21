# Domain Model

## Entities
| Entity | Responsibility |
|---|---|
| QualityRunner | Executes ruff/mypy on target files |
| AdapterFile | Source file under audit |
| QualityReport | Result artifact (JSON/text) |

## Relationships
- QualityRunner -> AdapterFile (analyzes)
- QualityRunner -> QualityReport (produces)
