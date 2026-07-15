from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
from datetime import datetime
from getpass import getpass
from pathlib import Path

from .client import RedcapClient
from .config import ConfigStore
from .errors import RedcapMcpError
from .models import Profile
from .secrets import delete_token, set_token
from .server import run_stdio


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="redcap-mcp", description="Read-only REDCap MCP configuration"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("setup", help="Interactively add a REDCap profile")
    add = commands.add_parser("profile-add", help="Add a profile non-interactively")
    add.add_argument("name")
    add.add_argument("url")
    add.add_argument("--default", action="store_true")
    add.add_argument("--ca-bundle")
    remove = commands.add_parser("profile-remove", help="Remove a profile")
    remove.add_argument("name")
    health = commands.add_parser("health", help="Check API connectivity")
    health.add_argument("--profile")
    alias = commands.add_parser("report-alias", help="Add or remove a saved-report alias")
    alias.add_argument("profile")
    alias.add_argument("alias")
    alias.add_argument("report_id", nargs="?")
    deny = commands.add_parser("protect-field", help="Add or remove an extra protected field")
    deny.add_argument("profile")
    deny.add_argument("field")
    deny.add_argument("--remove", action="store_true")
    ids = commands.add_parser("identifiers", help="Enable or disable profile identifier access")
    ids.add_argument("profile")
    ids.add_argument("state", choices=["enable", "disable"])
    ids.add_argument("--confirm", action="store_true")
    config = commands.add_parser("configure", help="Configure an MCP host")
    config.add_argument("host", choices=["codex", "claude-desktop", "claude-code"])
    commands.add_parser("serve", help="Run the MCP server over stdio")
    return parser


def _validated_profile(name: str, url: str, ca_bundle: str | None) -> Profile:
    if not name.replace("-", "").replace("_", "").isalnum():
        raise RedcapMcpError("Profile name may contain letters, numbers, hyphens, and underscores.")
    # REDCap commonly redirects `/api` to `/api/`. Store the canonical form so
    # first-time setup does not make an unnecessary redirect request.
    return Profile(name=name, api_url=url.strip().rstrip("/") + "/", ca_bundle=ca_bundle)


async def _check(profile: Profile, token: str) -> str:
    client = RedcapClient(profile, token)
    project = await client.project_info()
    return project.get("project_title", "")


def _add(store: ConfigStore, name: str, url: str, default: bool, ca_bundle: str | None) -> None:
    token = getpass("REDCap API token (stored in OS credential storage): ").strip()
    if not token:
        raise RedcapMcpError("A token is required.")
    profile = _validated_profile(name, url, ca_bundle)
    profile.project_title = asyncio.run(_check(profile, token))
    set_token(name, token)
    store.put_profile(profile, default)
    print(f"Configured profile '{name}'.")


def _host_config(host: str) -> Path:
    home = Path.home()
    if host == "claude-desktop":
        if sys.platform == "darwin":
            return home / "Library/Application Support/Claude/claude_desktop_config.json"
        return Path.home() / "AppData/Roaming/Claude/claude_desktop_config.json"
    if host == "claude-code":
        return home / ".claude.json"
    return home / ".codex/config.toml"


def _configure(host: str) -> None:
    path = _host_config(host)
    backup = None
    if path.exists():
        backup = path.with_name(path.name + "." + datetime.now().strftime("%Y%m%d%H%M%S") + ".bak")
        shutil.copy2(path, backup)
    import shutil as _shutil

    command = _shutil.which("redcap-mcp") or str(Path(sys.argv[0]).resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    if host == "codex":
        # Codex configuration is TOML. Append one isolated table instead of
        # rewriting the user's complete configuration file.
        content = path.read_text() if path.exists() else ""
        table = "[mcp_servers.redcap-api]"
        if table in content:
            raise RedcapMcpError(
                "A redcap-api Codex MCP entry already exists; edit it manually or remove it first."
            )
        with path.open("a", encoding="utf-8") as handle:
            if content and not content.endswith("\n"):
                handle.write("\n")
            handle.write(f'\n{table}\ncommand = {json.dumps(command)}\nargs = ["serve"]\n')
    else:
        data = json.loads(path.read_text()) if path.exists() else {}
        root = data.setdefault("mcpServers", {})
        root["redcap-api"] = {"command": command, "args": ["serve"]}
        path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Configured {host} at {path}" + (f" (backup: {backup})" if backup else ""))


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    store = ConfigStore()
    try:
        if args.command == "serve":
            run_stdio()
            return
        if args.command == "setup":
            name = input("Profile name: ").strip()
            url = input("REDCap API URL: ").strip()
            ca = input("Custom CA bundle (optional): ").strip() or None
            _add(store, name, url, True, ca)
        elif args.command == "profile-add":
            _add(store, args.name, args.url, args.default, args.ca_bundle)
        elif args.command == "profile-remove":
            store.remove_profile(args.name)
            delete_token(args.name)
            print("Profile removed.")
        elif args.command == "health":
            profile = store.get_profile(args.profile)
            title = asyncio.run(
                _check(
                    profile,
                    __import__("redcap_mcp.secrets", fromlist=["get_token"]).get_token(
                        profile.name
                    ),
                )
            )
            print(f"Healthy: {title or profile.name}")
        elif args.command == "report-alias":
            profile = store.get_profile(args.profile)
            if args.report_id:
                profile.report_aliases[args.alias] = args.report_id
            else:
                profile.report_aliases.pop(args.alias, None)
            store.put_profile(profile)
            print("Report aliases updated.")
        elif args.command == "protect-field":
            profile = store.get_profile(args.profile)
            values = set(profile.protected_fields)
            values.discard(args.field) if args.remove else values.add(args.field)
            profile.protected_fields = sorted(values)
            store.put_profile(profile)
            print("Protected fields updated.")
        elif args.command == "identifiers":
            if args.state == "enable" and not args.confirm:
                raise RedcapMcpError("Use --confirm to enable identifier access for this profile.")
            profile = store.get_profile(args.profile)
            profile.identifiers_enabled = args.state == "enable"
            store.put_profile(profile)
            print("Identifier policy updated.")
        elif args.command == "configure":
            _configure(args.host)
    except RedcapMcpError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
