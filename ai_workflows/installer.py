"""Installs plugin files to ~/.claude/ and ~/.local/bin/."""

import shutil
import stat
from importlib import resources
from pathlib import Path

CLAUDE_DIR  = Path.home() / ".claude"
AGENTS_DIR  = CLAUDE_DIR / "agents"
COMMANDS_DIR = CLAUDE_DIR / "commands"
RULES_DIR   = CLAUDE_DIR / "rules"
SCRIPTS_DIR = Path.home() / ".local" / "bin"

# Maps install source (within package) to destination
INSTALL_MAP = {
    "agents":   AGENTS_DIR,
    "commands": COMMANDS_DIR,
}


def _data_root() -> Path:
    """Return the path to bundled plugin/rule data, whether installed or running from source."""
    try:
        # Installed package: data was mapped into ai_workflows/ by hatchling
        ref = resources.files("ai_workflows")
        path = Path(str(ref))
        if (path / "plugins").exists():
            return path
    except Exception:
        pass
    # Running from source: data lives two levels up from this file
    return Path(__file__).parent.parent


def get_available_plugins() -> list[str]:
    """Return plugin slugs that have a plugin.yaml (i.e. are populated)."""
    plugins_dir = _data_root() / "plugins"
    return sorted(
        p.name
        for p in plugins_dir.iterdir()
        if p.is_dir() and not p.name.startswith("_") and (p / "plugin.yaml").exists()
    )


def _copy_file(src: Path, dest_dir: Path, dry_run: bool) -> tuple[Path, bool]:
    """Copy src into dest_dir. Returns (dest_path, was_overwritten)."""
    dest = dest_dir / src.name
    existed = dest.exists()
    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    return dest, existed


def _install_scripts(plugin_dir: Path, dry_run: bool) -> list[str]:
    scripts_src = plugin_dir / "scripts"
    if not scripts_src.exists():
        return []
    installed = []
    for src in sorted(scripts_src.iterdir()):
        if src.suffix not in (".py", ".sh") or not src.is_file():
            continue
        dest, existed = _copy_file(src, SCRIPTS_DIR, dry_run)
        if not dry_run:
            dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        label = "updated" if existed else "installed"
        installed.append(f"  {label} script  → {dest}")
    return installed


def _install_rules(data_root: Path, dry_run: bool) -> list[str]:
    rules_src = data_root / "rules"
    if not rules_src.exists():
        return []
    installed = []
    for src in sorted(rules_src.glob("*.md")):
        if src.stem == "README":
            continue
        dest, existed = _copy_file(src, RULES_DIR, dry_run)
        label = "updated" if existed else "installed"
        installed.append(f"  {label} rule    → {dest}")
    return installed


def install_plugin(slug: str, *, dry_run: bool = False, install_rules: bool = True) -> list[str]:
    """
    Install a plugin by slug. Returns a list of human-readable status lines.
    Raises FileNotFoundError if the plugin does not exist.
    """
    data_root = _data_root()
    plugin_dir = data_root / "plugins" / slug

    if not plugin_dir.exists():
        available = get_available_plugins()
        raise FileNotFoundError(
            f"Plugin '{slug}' not found. Available: {', '.join(available) or 'none'}"
        )

    lines: list[str] = []

    for subdir, dest_dir in INSTALL_MAP.items():
        src_dir = plugin_dir / subdir
        if not src_dir.exists():
            continue
        for src in sorted(src_dir.glob("*.md")):
            dest, existed = _copy_file(src, dest_dir, dry_run)
            label = "updated" if existed else "installed"
            lines.append(f"  {label} {subdir[:-1]:<7} → {dest}")

    lines.extend(_install_scripts(plugin_dir, dry_run))

    if install_rules:
        lines.extend(_install_rules(data_root, dry_run))

    return lines
