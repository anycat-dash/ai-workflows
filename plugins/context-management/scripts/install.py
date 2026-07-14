#!/usr/bin/env python3
"""
Install context-management skills declared in plugin.yaml.

Idempotent: skills already present in skills-lock.json are skipped.

Usage:
    install.py [--dry-run] [--repo-root DIR]
"""

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

REPO_ROOT    = Path(__file__).parent.parent.parent.parent  # ai-workflows root
PLUGIN_YAML  = Path(__file__).parent.parent / "plugin.yaml"
SKILLS_DIR   = REPO_ROOT / ".agents" / "skills"
LOCK_FILE    = REPO_ROOT / "skills-lock.json"
RAW_BASE     = "https://raw.githubusercontent.com"


# ---------------------------------------------------------------------------
# Lock file
# ---------------------------------------------------------------------------

def read_lock() -> dict:
    if LOCK_FILE.exists():
        return json.loads(LOCK_FILE.read_text())
    return {"version": 1, "skills": {}}


def write_lock(lock: dict) -> None:
    LOCK_FILE.write_text(json.dumps(lock, indent=2) + "\n")


def skill_key(path: str) -> str:
    """Derive the skill name from its path (e.g. skills/caveman/SKILL.md → caveman)."""
    return Path(path).parent.name


def is_installed(skill_name: str, source: str, skill_path: str, lock: dict) -> bool:
    entry = lock["skills"].get(skill_name)
    if not entry:
        return False
    return (
        entry.get("source") == source
        and entry.get("skillPath") == skill_path
        and (SKILLS_DIR / skill_name / "SKILL.md").exists()
    )


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_raw(source: str, path: str) -> str:
    url = f"{RAW_BASE}/{source}/HEAD/{path}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:  # noqa: S310
            return resp.read().decode()
    except Exception as e:
        raise RuntimeError(f"failed to fetch {url}: {e}") from e


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

def install_skill(source: str, skill_path: str, *, dry_run: bool) -> str:
    """
    Download a single SKILL.md. Returns a status string.
    skill_path is the path within the source repo (e.g. skills/caveman/SKILL.md).
    """
    skill_name = skill_key(skill_path)
    dest_dir = SKILLS_DIR / skill_name
    dest = dest_dir / "SKILL.md"

    content = fetch_raw(source, skill_path)
    digest = compute_hash(content)

    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)

    return digest


def load_plugin_yaml() -> dict:
    """Parse plugin.yaml with a minimal YAML parser (no third-party deps)."""
    try:
        import yaml  # type: ignore
        return yaml.safe_load(PLUGIN_YAML.read_text())
    except ImportError:
        pass

    sys.exit(
        "error: PyYAML is required to parse plugin.yaml.\n"
        "Install it with: uv pip install pyyaml\n"
        "Or run via the ai-workflows CLI which handles this automatically."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Install context-management skills.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be installed without writing files")
    parser.add_argument("--repo-root", type=Path, help="Override repo root (default: auto-detected)")
    args = parser.parse_args()

    global REPO_ROOT, SKILLS_DIR, LOCK_FILE
    if args.repo_root:
        REPO_ROOT  = args.repo_root.resolve()
        SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
        LOCK_FILE  = REPO_ROOT / "skills-lock.json"

    config = load_plugin_yaml()
    skills_to_install: list[dict] = config.get("skills", [])

    if not skills_to_install:
        print("No skills declared in plugin.yaml.")
        return

    lock = read_lock()
    updated = False

    for group in skills_to_install:
        source     = group["source"]
        paths      = group.get("paths", [])

        for skill_path in paths:
            skill_name = skill_key(skill_path)

            if is_installed(skill_name, source, skill_path, lock):
                print(f"  skip    {skill_name:<24} (already installed)")
                continue

            dry = " (dry run)" if args.dry_run else ""
            print(f"  install {skill_name:<24} ← {source}/{skill_path}{dry}")

            if not args.dry_run:
                try:
                    digest = install_skill(source, skill_path, dry_run=False)
                except RuntimeError as e:
                    print(f"  error   {skill_name}: {e}", file=sys.stderr)
                    continue

                lock["skills"][skill_name] = {
                    "source":       source,
                    "sourceType":   group.get("sourceType", "github"),
                    "skillPath":    skill_path,
                    "computedHash": digest,
                }
                updated = True

    if updated and not args.dry_run:
        write_lock(lock)
        print("\nUpdated skills-lock.json.")

    if not args.dry_run:
        print("\nDone. Restart Claude Code to pick up new skills.")


if __name__ == "__main__":
    main()
