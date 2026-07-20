"""Installs plugin files to ~/.claude/ and ~/.local/bin/."""

import subprocess
import shutil
import stat
import sys
from importlib import resources
from pathlib import Path

CLAUDE_DIR  = Path.home() / ".claude"
AGENTS_DIR  = CLAUDE_DIR / "agents"
COMMANDS_DIR = CLAUDE_DIR / "commands"
RULES_DIR   = CLAUDE_DIR / "rules"
SKILLS_DIR  = CLAUDE_DIR / "skills"
SKILLS_LOCK = CLAUDE_DIR / "skills-lock.json"
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


def _remove_file(path: Path, dry_run: bool) -> bool:
    if not path.exists():
        return False
    if not dry_run:
        path.unlink()
    return True


def _load_plugin_yaml(plugin_dir: Path) -> dict:
    plugin_yaml = plugin_dir / "plugin.yaml"
    if not plugin_yaml.exists():
        return {}
    try:
        import yaml  # type: ignore
    except ImportError:
        return {}
    try:
        return yaml.safe_load(plugin_yaml.read_text()) or {}
    except Exception:
        return {}


def _remove_bundle_skills(plugin_dir: Path, dry_run: bool) -> list[str]:
    """Remove skills fetched by this plugin's bundle from ~/.claude/skills/ and skills-lock.json."""
    config = _load_plugin_yaml(plugin_dir)
    skill_groups = config.get("skills") or []
    if not skill_groups:
        return []

    import json
    lock = {}
    if SKILLS_LOCK.exists():
        try:
            lock = json.loads(SKILLS_LOCK.read_text())
        except Exception:
            lock = {"version": 1, "skills": {}}
    lock.setdefault("skills", {})

    lines: list[str] = []
    for group in skill_groups:
        for path in group.get("paths", []):
            skill_name = Path(path).parent.name
            skill_dir = SKILLS_DIR / skill_name
            if skill_dir.exists():
                if not dry_run:
                    shutil.rmtree(skill_dir)
                lines.append(f"  removed skill   ← {skill_dir}")
            lock["skills"].pop(skill_name, None)

    if lines and not dry_run and SKILLS_LOCK.exists():
        SKILLS_LOCK.write_text(json.dumps(lock, indent=2) + "\n")
    return lines


def _run_post_uninstall(plugin_dir: Path, dry_run: bool) -> list[str]:
    """
    Run `postUninstall` hooks from plugin.yaml. Same shape as postInstall, but `check` semantics
    reversed: if `check` command FAILS (thing not installed), skip the hook.
    """
    config = _load_plugin_yaml(plugin_dir)
    hooks = config.get("postUninstall") or []
    if not hooks:
        return []

    lines: list[str] = []
    for hook in hooks:
        desc = hook.get("description") or hook.get("command", "<unnamed>")
        check = hook.get("check")
        cmd = hook.get("command")
        if not cmd:
            continue

        if check:
            present = subprocess.run(check, shell=True, capture_output=True).returncode == 0
            if not present:
                lines.append(f"  skip postUninstall: {desc} (not installed)")
                continue

        if dry_run:
            lines.append(f"  would run: {desc} → `{cmd}` (dry run)")
            continue

        lines.append(f"  running postUninstall: {desc}")
        print(lines[-1], flush=True)
        rc = _stream_shell(cmd, prefix="    ")
        if rc != 0:
            lines.append(f"  postUninstall failed (exit {rc}): {desc}")
    return lines


def uninstall_plugin(slug: str, *, dry_run: bool = False, remove_rules: bool = False) -> list[str]:
    """Remove files this plugin installed. Returns status lines."""
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
            dest = dest_dir / src.name
            if _remove_file(dest, dry_run):
                lines.append(f"  removed {subdir[:-1]:<7} ← {dest}")

    scripts_src = plugin_dir / "scripts"
    if scripts_src.exists():
        for src in sorted(scripts_src.iterdir()):
            if src.suffix not in (".py", ".sh") or not src.is_file():
                continue
            dest = SCRIPTS_DIR / src.name
            if _remove_file(dest, dry_run):
                lines.append(f"  removed script  ← {dest}")

    lines.extend(_remove_bundle_skills(plugin_dir, dry_run))
    lines.extend(_run_post_uninstall(plugin_dir, dry_run))

    if remove_rules:
        rules_src = data_root / "rules"
        if rules_src.exists():
            for src in sorted(rules_src.glob("*.md")):
                if src.stem == "README":
                    continue
                dest = RULES_DIR / src.name
                if _remove_file(dest, dry_run):
                    lines.append(f"  removed rule    ← {dest}")

    return lines


def _run_bundle_script(plugin_dir: Path, dry_run: bool) -> list[str]:
    """
    If plugin.yaml declares `skills:`, run the plugin's bundle installer script
    (e.g. scripts/install.py or scripts/init.py) pointed at ~/.claude/skills/.
    """
    plugin_yaml = plugin_dir / "plugin.yaml"
    if not plugin_yaml.exists():
        return []

    try:
        import yaml  # type: ignore
    except ImportError:
        return [f"  skip bundle (pyyaml missing): {plugin_dir.name}"]

    try:
        config = yaml.safe_load(plugin_yaml.read_text()) or {}
    except Exception as e:
        return [f"  error reading {plugin_yaml}: {e}"]

    if not config.get("skills"):
        return []

    compat = (config.get("compatibility") or {}).get("claude-code") or {}
    script_paths = compat.get("scripts") or []
    if not script_paths:
        return [f"  skip bundle ({plugin_dir.name}): no scripts declared in plugin.yaml"]

    script = plugin_dir / script_paths[0]
    if not script.exists():
        return [f"  error: bundle script not found: {script}"]

    cmd = [
        sys.executable, str(script),
        "--skills-dir", str(SKILLS_DIR),
        "--lock-file", str(SKILLS_LOCK),
    ]
    if dry_run:
        cmd.append("--dry-run")

    lines = [f"  running bundle script: {script.name}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except Exception as e:
        return lines + [f"  error running bundle: {e}"]

    for out in (result.stdout, result.stderr):
        for ln in out.splitlines():
            if ln.strip():
                lines.append(f"    {ln}")
    if result.returncode != 0:
        lines.append(f"  bundle script failed (exit {result.returncode})")
    return lines


def _run_post_install(plugin_dir: Path, dry_run: bool) -> list[str]:
    """
    Run `postInstall` hooks declared in plugin.yaml. Each hook is:
      - description: str
        check: str (optional shell command; if exit 0, hook is skipped as already-installed)
        command: str (shell command to run)
    """
    plugin_yaml = plugin_dir / "plugin.yaml"
    if not plugin_yaml.exists():
        return []
    try:
        import yaml  # type: ignore
    except ImportError:
        return []
    try:
        config = yaml.safe_load(plugin_yaml.read_text()) or {}
    except Exception:
        return []

    hooks = config.get("postInstall") or []
    if not hooks:
        return []

    lines: list[str] = []
    for hook in hooks:
        desc = hook.get("description") or hook.get("command", "<unnamed>")
        check = hook.get("check")
        cmd = hook.get("command")
        if not cmd:
            continue

        if check:
            already = subprocess.run(check, shell=True, capture_output=True).returncode == 0
            if already:
                lines.append(f"  skip postInstall: {desc} (already installed)")
                continue

        if dry_run:
            lines.append(f"  would run: {desc} → `{cmd}` (dry run)")
            continue

        lines.append(f"  running postInstall: {desc}")
        print(lines[-1], flush=True)
        rc = _stream_shell(cmd, prefix="    ")
        if rc != 0:
            lines.append(f"  postInstall failed (exit {rc}): {desc}")
    return lines


def _stream_shell(cmd: str, *, prefix: str = "") -> int:
    """Run a shell command, streaming stdout/stderr live to the terminal. Returns exit code."""
    proc = subprocess.Popen(
        cmd, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        print(f"{prefix}{line.rstrip()}", flush=True)
    return proc.wait()


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
    lines.extend(_run_bundle_script(plugin_dir, dry_run))
    lines.extend(_run_post_install(plugin_dir, dry_run))

    if install_rules:
        lines.extend(_install_rules(data_root, dry_run))

    return lines
