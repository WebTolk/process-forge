# Codex hook registration and conversation audit

- Before this slice the adapter accepted raw events and captured only `UserPromptSubmit` content. Generic final assistant and subagent answers were absent from the PF transcript.
- Codex documents `last_assistant_message` on `Stop` and `SubagentStop`.
- Adapter capability is not registration proof: the distribution previously wrote no `.codex/hooks.json`.
- The installer manages eight observation events, but actual use requires the target project config to be loaded and trusted (`/hooks`).

The conversation smoke proves prompt, main final and subagent final capture; it also proves repeat delivery produces the same message id and leaves content out of project events.
