#!/usr/bin/env python3
"""
Scaffold the scratchpad for a new orchestrator run.

Usage:
    orchestrator-init.py --task "<description>" --slug <slug> [--dry-run]

Creates:
    ~/scratchpad/orchestrator/<slug>/
        state.json
        iterations/
        quality/

Idempotent: if the directory exists, updates state.json only.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def scratchpad_root() -> Path:
    return Path.home() / "scratchpad" / "orchestrator"


def scaffold(slug: str, task: str, *, dry_run: bool) -> Path:
    root = scratchpad_root() / slug
    state_path = root / "state.json"

    if dry_run:
        print(f"[dry-run] would create {root}/")
        print(f"[dry-run] would write {state_path}")
        return root

    (root / "iterations").mkdir(parents=True, exist_ok=True)
    (root / "quality").mkdir(parents=True, exist_ok=True)

    if state_path.exists():
        state = json.loads(state_path.read_text())
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
    else:
        state = {
            "task": task,
            "slug": slug,
            "phase": "architect",
            "iteration": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    return root


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold orchestrator scratchpad.")
    parser.add_argument("--task", required=True, help="One-line task description")
    parser.add_argument("--slug", required=True, help="Task slug (kebab-case)")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = parser.parse_args()

    if not args.slug.replace("-", "").isalnum():
        sys.exit(f"error: slug must be kebab-case alphanumerics: {args.slug!r}")

    path = scaffold(args.slug, args.task, dry_run=args.dry_run)
    print(str(path))


if __name__ == "__main__":
    main()
