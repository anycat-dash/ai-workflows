# Plugin Name

> One-line summary.

## What it does

Describe the problem this plugin solves and how it helps the agent work faster or more accurately.

## Setup

### Claude Code

Add to `.claude/subagents.json` (or merge into the array if the file already exists):

```json
{
  "name": "plugin-name",
  "description": "One-line description so Claude knows when to delegate to this subagent.",
  "model": "claude-haiku-4-5-20251001",
  "systemPrompt": "You are a specialized agent focused on <task>. Only use the tools listed below. Return concise, structured output to the coordinator.",
  "tools": ["Read", "Grep", "Glob", "Bash"]
}
```

Full config: [`config/claude.json`](./config/claude.json)

---

### Codex

Add to your Codex agent definition or pass via the Agents SDK:

```json
{
  "agent": {
    "name": "plugin-name",
    "description": "One-line description used for routing by the coordinator agent.",
    "model": "o4-mini",
    "instructions": "You are a specialized agent focused on <task>. Return structured output so the coordinator can consolidate results.",
    "tools": []
  }
}
```

Full config: [`config/codex.json`](./config/codex.json)

---

### OpenCode

Create a markdown file at `~/.config/opencode/agents/plugin-name.md` (global) or `.opencode/agents/plugin-name.md` (project-local):

```yaml
---
name: plugin-name
description: One-line description used by the coordinator to decide when to spawn this agent.
model: anthropic/claude-haiku-4-5
tools:
  - read
  - grep
---

You are a specialized agent focused on <task>.
Keep responses concise and structured.
```

Full config: [`config/opencode.yaml`](./config/opencode.yaml)

---

## Usage

Show example prompts or agent interactions that demonstrate the plugin in action.

## Why it's useful

Explain the efficiency gain — time saved, errors avoided, context preserved, etc.
