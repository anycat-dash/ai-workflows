# Documentation Plugin

> Install skills that help agents read, write, and navigate documentation.

## What it does

Reads the skill bundle declared in `plugin.yaml` and installs any skills not yet present in `.agents/skills/` and `skills-lock.json`. Already-installed skills are silently skipped.

## Bundle

| Skill | Source | Description |
|-------|--------|-------------|
| openspec | `openspec/openspec` | _(TODO: verify repo slug)_ |
| openwiki | `openwiki/openwiki` | _(TODO: verify repo slug)_ |

## Usage

```bash
# Dry run — show what would be installed
python3 plugins/documentation/scripts/install.py --dry-run

# Install missing skills
python3 plugins/documentation/scripts/install.py

# Via the ai-workflows CLI (once bundle install support is added)
ai-workflows install documentation
```

## Idempotency

A skill is considered already installed when:
1. Its `name` key exists in `skills-lock.json`, **and**
2. Its `source` and `skillPath` match the declared values, **and**
3. The SKILL.md file exists on disk at `.agents/skills/<name>/SKILL.md`

If any of these three conditions fails, the skill is reinstalled.
