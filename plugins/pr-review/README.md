# PR Review Plugin

> Structured pull request review workflows with parallel specialized subagents, security auditing, and stale PR triage.

## What it does

Orchestrates a multi-agent PR review pipeline. A coordinator spawns specialized subagents in parallel — each focused on a single review lens (correctness, security, quality, testing) — then consolidates findings into structured, line-level comments posted to GitHub. Separate skills handle standalone security audits and stale PR triage.

## Components

### Agents (subagents)

| Agent | Description | Tools |
|-------|-------------|-------|
| [reviewer](./agents/reviewer.md) | Coordinator — read-only PR review, delegates to specialist subagents | Read, Grep, Glob, Bash, Atlassian, Glean |
| [correctness-reviewer](./agents/correctness-reviewer.md) | Race conditions, null handling, transaction integrity, algorithmic bugs | Read, Grep, Glob, Bash |
| [security-reviewer](./agents/security-reviewer.md) | Auth, injection, PII, secrets, and API risks | Read, Grep, Glob, Bash |
| [quality-reviewer](./agents/quality-reviewer.md) | Duplication, OOP violations, optimization opportunities | Read, Grep, Glob, Bash |
| [testing-reviewer](./agents/testing-reviewer.md) | Missing tests, fragile setup, mock abuse, assertion quality | Read, Grep, Glob, Bash |
| [finding-verifier](./agents/finding-verifier.md) | Reproduces a finding in an isolated worktree; drops false positives | Read, Grep, Glob, Bash, Write |
| [research](./agents/research.md) | Internal doc/Slack search via Glean; no code edits | (Glean, Atlassian) |

### Scripts

| Script | Description |
|--------|-------------|
| [pr-review-preflight.py](./scripts/pr-review-preflight.py) | Fetches PR metadata, creates a git worktree, generates `diff.txt`, categorises changed files, scaffolds the review directory |
| [post-pr-review.py](./scripts/post-pr-review.py) | Validates and posts the drafted review as a single atomic GitHub review; resolves threads via GraphQL |
| [pr-review-buckets.json](./scripts/pr-review-buckets.json) | Source of truth for file-extension → bucket → lens mapping (edit this to add languages or change which lenses run) |

### Commands (slash commands)

| Command | Description |
|---------|-------------|
| [/fresh-eyes](./commands/fresh-eyes.md) | Unbiased review of uncommitted local changes (`git diff HEAD`) without posting to GitHub |
| [/cve-diff](./commands/cve-diff.md) | Compare npm audit CVEs between current branch and default branch |

### Skills

| Skill | Description |
|-------|-------------|
| [pr-review](./skills/pr-review/SKILL.md) | Full PR review with structured analysis and line-level GitHub comments |
| [stale-pr-triage](./skills/stale-pr-triage/SKILL.md) | Determine if an old PR should be closed, reimplemented, or merged |
| [insecure-defaults](./skills/insecure-defaults/SKILL.md) | Standalone codebase audit for fail-open patterns, hardcoded credentials, and weak crypto |

## Setup

### Claude Code

Copy the agent files into your project or global subagents directory:

```bash
# Project-local
cp agents/*.md .claude/agents/

# Global
cp agents/*.md ~/.claude/agents/
```

Register skills in `.claude/settings.json`:

```json
{
  "skills": [
    "skills/pr-review/SKILL.md",
    "skills/stale-pr-triage/SKILL.md",
    "skills/insecure-defaults/SKILL.md"
  ]
}
```

Register commands in `.claude/settings.json`:

```json
{
  "commands": [
    "commands/fresh-eyes.md",
    "commands/cve-diff.md"
  ]
}
```

### Codex / OpenCode

Not yet configured. See `_template/config/` for the format to follow.

## Usage

```
# Full PR review
/pr-review https://github.com/org/repo/pull/123

# Quick review of local changes before pushing
/fresh-eyes

# Check if a PR is still worth merging
/stale-pr-triage https://github.com/org/repo/pull/456

# Audit for insecure defaults
/insecure-defaults

# Compare CVE exposure between branches
/cve-diff
```

## Dependencies

These shared rules must be present for the plugin to work correctly:

| Rule | Used by |
|------|---------|
| [`pr-disclaimers`](../../rules/pr-disclaimers.md) | All posting agents and skills |
| [`pr-review-principles`](../../rules/pr-review-principles.md) | `reviewer`, `fresh-eyes`, `pr-review` skill |
| [`scratchpad`](../../rules/scratchpad.md) | `pr-review` skill, `cve-diff`, `stale-pr-triage` |
| [`local-repos`](../../rules/local-repos.md) | `stale-pr-triage` skill |
| [`search`](../../rules/search.md) | `security-reviewer`, `research` |
| [`jira`](../../rules/jira.md) | `research` agent |

## Why it's useful

- **Parallel reviewers** cut review time vs. a single agent doing everything sequentially
- **Scoped tool access** per subagent prevents reviewers from making accidental edits
- **Finding verifier** eliminates false positives before comments are posted
- **`/fresh-eyes`** gives a clean second opinion without GitHub noise
