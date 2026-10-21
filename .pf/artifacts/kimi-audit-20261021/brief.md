# Brief: Аудит kimi-* адаптеров

## Problem
Kimi-* адаптеры (kimi_hooks.py, kimi_adapters.py, builtin_provider_adapters.py) требуют проверки качества кода.

## Goal
Запустить ruff и mypy, исправить найденные проблемы, записать отчёты.

## Non-Goals
- Не менять архитектуру или API.
- Не добавлять новые функции.
