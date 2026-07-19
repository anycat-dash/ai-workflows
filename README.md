# ai-workflows

Curated plugins, agents, and skills for coding assistants — Claude Code first, Codex + OpenCode on the roadmap.

The repo is both:
- A **plugin library** — drop-in `plugins/<category>/<plugin>/` bundles with agents, slash commands, skills, scripts.
- A **Python package** (`ai_workflows`) — a CLI installer that copies plugin assets into `~/.claude/` (or the target agent's config dir).

## Highlights

| Plugin | What it does |
|--------|--------------|
| [`orchestrator`](./plugins/orchestrator/) | Multi-agent PR delivery: architect → implementer (stacked PRs, worktrees) → code review → QA → last-mile merge. Two human gates. |
| [`pr-review`](./plugins/pr-review/) | Structured PR review with parallel specialized subagents (security, correctness, quality, testing), stale-PR triage, insecure-defaults audit. |
| [`context-management`](./plugins/context-management/) | Token-efficient communication skills (caveman) and context tools (headroomai). |
| [`documentation`](./plugins/documentation/) | Spec + docs skills — openspec, openwiki. |
| [`init`](./plugins/init/) | Bootstrap installer bundle (idempotent skill fetch from GitHub). |

See [`plugins/README.md`](./plugins/README.md) for the full category index.

## Install

Via `uv` (recommended) or `pip`:

```bash
uv pip install -e .
# or
pip install -e .
```

Then install plugins into your Claude config:

```bash
ai-workflows list                 # show available plugins
ai-workflows install pr-review    # install one plugin
ai-workflows install orchestrator
```

The installer copies:
- `agents/*.md` → `~/.claude/agents/`
- `commands/*.md` → `~/.claude/commands/`
- `skills/**` → `~/.claude/skills/`
- `scripts/*` → `~/.local/bin/` (with `+x`)
- Referenced `rules/*.md` → `~/.claude/rules/`

Restart Claude Code after installing so it picks up the new agents/skills.

## Repo layout

```
ai-workflows/
├── ai_workflows/          # Python package (installer + CLI)
│   ├── cli.py             # `ai-workflows` entrypoint
│   └── installer.py       # copy-to-Claude-config logic
├── plugins/               # plugin library
│   ├── _template/         # scaffold to copy when creating new plugins
│   ├── orchestrator/      # multi-agent PR delivery
│   ├── pr-review/         # PR review workflows
│   └── ...                # other categories
├── rules/                 # shared rules referenced by multiple plugins
│   ├── pr-disclaimers.md
│   ├── pr-review-principles.md
│   ├── scratchpad.md
│   └── ...
├── skills-lock.json       # lock file for skills fetched from external repos
├── pyproject.toml
└── README.md              # you are here
```

### Plugin anatomy

Each plugin lives at `plugins/<category-or-slug>/` and contains:

```
plugin.yaml               # metadata: name, version, category, tags, compat
README.md                 # user docs
agents/*.md               # subagent definitions (frontmatter + prompt body)
commands/*.md             # slash commands (Claude Code)
skills/<slug>/SKILL.md    # workflow skills
scripts/*.{py,sh,json}    # supporting scripts
config/                   # per-agent config templates (optional)
```

See [`plugins/_template/`](./plugins/_template/) for the canonical scaffold.

### Shared rules

Cross-plugin conventions live under [`rules/`](./rules/). Plugins reference them by name (e.g. `` `scratchpad` rule ``). The installer copies referenced rules into `~/.claude/rules/`.

## Adding a plugin

1. Copy `plugins/_template/` to `plugins/<your-slug>/`.
2. Fill in `plugin.yaml` (name, description, category, compat block).
3. Author agents / commands / skills / scripts as needed.
4. Add an index entry to `plugins/README.md` and (if user-facing) this README's Highlights table.
5. Test with `ai-workflows install <your-slug>` in a scratch config.

## Compatibility matrix

| Target | Status |
|--------|--------|
| Claude Code (agents, slash commands, skills) | Supported |
| OpenAI Codex | Placeholder in `plugin.yaml`, no bundled configs yet |
| OpenCode | Placeholder in `plugin.yaml`, no bundled configs yet |

Only Claude Code is wired end-to-end today. Codex + OpenCode support is trending toward parity via per-plugin config templates in `config/`.

## License

MIT (see plugin-level `plugin.json` / `plugin.yaml` for per-plugin attribution).

## Maintainer

`anycat_blank`
