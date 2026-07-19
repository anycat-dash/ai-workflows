# Coding Agent Plugins

A curated collection of plugins, tools, and configurations to drive efficiency in coding agents.

## Compatible Agents

| Agent | Config Format |
|-------|--------------|
| Claude Code | MCP servers, hooks, skills (slash commands) |
| OpenAI Codex | tools JSON |
| OpenCode | plugins YAML |

## Categories

| Category | Description |
|----------|-------------|
| [documentation](./documentation/) | Docstring gen, README, changelogs |
| [context-management](./context-management/) | Memory, summarization, project indexing |
| [init](./init/) | Bootstrap installer bundle |
| [orchestrator](./orchestrator/) | End-to-end multi-agent PR delivery |
| [pr-review](./pr-review/) | PR review automation, diff analysis, comment generation — 7 subagents, 2 commands, 3 skills |

## Adding a Plugin

1. Copy `_template/` into the relevant category folder
2. Rename it to your plugin slug (kebab-case)
3. Fill in `plugin.yaml` and `README.md`
4. Add an entry to this README's index (coming soon: auto-generated)

## Plugin Structure

Each plugin lives in its own directory:

```
plugins/<category>/<plugin-name>/
├── plugin.yaml       # metadata + agent compatibility
├── README.md         # usage, examples, rationale
└── config/
    ├── claude.json   # Claude Code config (MCP / hook / skill)
    ├── codex.json    # Codex tools config
    └── opencode.yaml # OpenCode plugin config
```
