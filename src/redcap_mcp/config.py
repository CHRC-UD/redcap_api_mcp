from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .errors import ConfigurationError
from .models import Profile

SERVICE = "redcap-api-mcp"


def config_path() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "redcap-api-mcp" / "config.json"


class ConfigStore:
    def __init__(self, path: Path | None = None):
        self.path = path or config_path()

    def load(self) -> dict[str, object]:
        if not self.path.exists():
            return {"profiles": {}, "default_profile": None}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError("Configuration could not be read.") from exc
        if not isinstance(value, dict) or not isinstance(value.get("profiles", {}), dict):
            raise ConfigurationError("Configuration has an invalid format.")
        return value

    def save(self, config: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(self.path)

    def profiles(self) -> dict[str, Profile]:
        return {name: Profile.from_dict(value) for name, value in self.load()["profiles"].items()}  # type: ignore[union-attr]

    def get_profile(self, name: str | None = None) -> Profile:
        cfg = self.load()
        selected = name or cfg.get("default_profile")
        profiles = cfg["profiles"]
        if not selected or selected not in profiles:  # type: ignore[operator]
            raise ConfigurationError("No matching REDCap profile is configured.")
        return Profile.from_dict(profiles[selected])  # type: ignore[index,arg-type]

    def put_profile(self, profile: Profile, default: bool = False) -> None:
        cfg = self.load()
        profiles = cfg["profiles"]
        profiles[profile.name] = profile.to_dict()  # type: ignore[index]
        if default or not cfg.get("default_profile"):
            cfg["default_profile"] = profile.name
        self.save(cfg)

    def remove_profile(self, name: str) -> None:
        cfg = self.load()
        if name not in cfg["profiles"]:  # type: ignore[operator]
            raise ConfigurationError("No matching REDCap profile is configured.")
        del cfg["profiles"][name]  # type: ignore[index]
        if cfg.get("default_profile") == name:
            cfg["default_profile"] = next(iter(cfg["profiles"]), None)  # type: ignore[index]
        self.save(cfg)
