# Init Plugin

> Bootstrap a Claude environment by installing a curated set of skills. Idempotent — safe to re-run.

## What it does

Reads the skill bundle declared in `plugin.yaml` and installs any skills not yet present in `.agents/skills/` and `skills-lock.json`. Already-installed skills are silently skipped.

## Bundle

| Skill | Source | Description |
|-------|--------|-------------|
| _(none yet)_ | | |

## Usage

```bash
# Dry run — show what would be installed
python3 plugins/init/scripts/init.py --dry-run

# Install missing skills
python3 plugins/init/scripts/init.py

# Via the ai-workflows CLI (once bundle install support is added)
ai-workflows install init
```

## Idempotency

A skill is considered already installed when:
1. Its `name` key exists in `skills-lock.json`, **and**
2. Its `source` and `skillPath` match the declared values, **and**
3. The SKILL.md file exists on disk at `.agents/skills/<name>/SKILL.md`

If any of these three conditions fails, the skill is reinstalled.

## Adding skills to the bundle

Edit `plugin.yaml` and add an entry under `skills:`:

```yaml
skills:
  - name: my-skill
    source: github-org/repo
    sourceType: github
    paths:
      - skills/my-skill/SKILL.md
```
