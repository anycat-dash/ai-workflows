# Orchestrator Plugin

> End-to-end feature delivery via a chain of specialized Claude subagents. Architect designs, Implementer codes, Reviewer critiques, Quality tests, Last Mile merges.

## Flow

```
user → /orchestrate <task-description>
  0. Precheck                    — verify $PWD/openspec exists (else halt)
  1. Architect      (Opus 4.7)   — openspec proposal + design + tasks.md
  2. [HUMAN GATE]                — approve spec
  3. Implementer    (Sonnet 4.6) — code + PR (no architect memory)
  4. Code Review    (reviewer)   — assess-only, no posting
     └─ loop 3 ↔ 4 up to 3 iterations
  5. Quality        (Sonnet 4.6) — run tests, add missing coverage
  6. [HUMAN GATE]                — approve before merge
  7. Last Mile      (Sonnet 4.6) — wait for CI, merge PR
  8. Cleanup                     — if merged, remove scratchpad
```

## Agents

| Agent | Model | Role |
|-------|-------|------|
| `architect` | `claude-opus-4-7` | Senior architect + software eng expert. Writes proposal/design/tasks.md via openspec skill. |
| `implementer` | `claude-sonnet-4-6` | Senior software engineer. Follows tasks.md, opens/updates PR. No architect memory. |
| `quality` | `claude-sonnet-4-6` | Senior QA. Runs unit tests, adds missing tests, ensures build+test pass. |
| `last-mile` | `claude-sonnet-4-6` | Waits for CI green, merges PR. |

Code review reuses the `reviewer` agent from the `pr-review` plugin (assess-only mode).

## Usage

```
/orchestrate add a --version flag to the CLI
```

Orchestrator will pause twice for human approval:
1. After architect produces the spec — reply `approve` or `changes: <notes>`.
2. Before merge — same protocol.

## Prerequisites

- `openspec` initialized in the working repo (`openspec init`).
- `gh` CLI authenticated for PR creation/merge.
- `pr-review` plugin installed (orchestrator reuses its `reviewer` agent).

## Artifacts

- **Specs**: `$PWD/openspec/` (managed by openspec skill).
- **Runtime state**: `~/scratchpad/orchestrator/<task-slug>/`
  - `state.json` — phase + iteration counter
  - `spec-refs.json` — pointers into `$PWD/openspec/`
  - `pr.json` — PR metadata
  - `iterations/i-N/review.json` — reviewer findings per loop
  - `quality/report.md` — QA output
- **Cleanup**: scratchpad is removed after successful merge only.

## Configuration

Loop cap for implementation ↔ review: **3 iterations** (hard-coded in skill).

## Compatibility

Claude Code only for v0.1. Codex / OpenCode not supported.
