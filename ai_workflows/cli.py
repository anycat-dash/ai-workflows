"""CLI entry point for ai-workflows."""

import argparse
import sys

from .installer import get_available_plugins, install_plugin, uninstall_plugin


def cmd_install(args: argparse.Namespace) -> int:
    slugs: list[str] = args.plugin
    if "all" in slugs:
        slugs = get_available_plugins()
        if not slugs:
            print("No plugins available.", file=sys.stderr)
            return 1

    rules_installed = False
    for slug in slugs:
        dry = " (dry run)" if args.dry_run else ""
        print(f"\nInstalling '{slug}'{dry}:")
        try:
            # Only install shared rules once across multiple plugins
            lines = install_plugin(slug, dry_run=args.dry_run, install_rules=not rules_installed)
            rules_installed = True
        except FileNotFoundError as e:
            print(f"  error: {e}", file=sys.stderr)
            return 1
        if lines:
            print("\n".join(lines))
        else:
            print("  nothing to install.")

    if not args.dry_run:
        print("\nDone. Restart Claude Code to pick up new agents and commands.")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    slugs: list[str] = args.plugin
    if "all" in slugs:
        slugs = get_available_plugins()
        if not slugs:
            print("No plugins available.", file=sys.stderr)
            return 1

    last = len(slugs) - 1
    for i, slug in enumerate(slugs):
        dry = " (dry run)" if args.dry_run else ""
        print(f"\nUninstalling '{slug}'{dry}:")
        try:
            lines = uninstall_plugin(
                slug, dry_run=args.dry_run, remove_rules=args.rules and i == last
            )
        except FileNotFoundError as e:
            print(f"  error: {e}", file=sys.stderr)
            return 1
        print("\n".join(lines) if lines else "  nothing to remove.")
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    plugins = get_available_plugins()
    if not plugins:
        print("No plugins available.")
        return 0
    print("Available plugins:")
    for slug in plugins:
        print(f"  {slug}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-workflows",
        description="Install AI workflow plugins to ~/.claude/",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    install = sub.add_parser("install", help="Install one or more plugins")
    install.add_argument(
        "plugin",
        nargs="+",
        metavar="<plugin|all>",
        help="Plugin slug(s) to install, or 'all'",
    )
    install.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be installed without writing any files",
    )
    install.set_defaults(func=cmd_install)

    uninstall = sub.add_parser("uninstall", help="Remove installed plugin files from ~/.claude/")
    uninstall.add_argument("plugin", nargs="+", metavar="<plugin|all>")
    uninstall.add_argument("--dry-run", action="store_true")
    uninstall.add_argument("--rules", action="store_true", help="Also remove shared rules")
    uninstall.set_defaults(func=cmd_uninstall)

    list_cmd = sub.add_parser("list", help="List available plugins")
    list_cmd.set_defaults(func=cmd_list)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
