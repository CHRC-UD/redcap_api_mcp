from __future__ import annotations

import secrets

from .errors import ConfigurationError

try:
    import keyring
except ImportError:  # pragma: no cover - dependency is required at runtime
    keyring = None


def _require_keyring() -> None:
    if keyring is None:
        raise ConfigurationError(
            "OS credential storage is unavailable; install the keyring dependency."
        )


def get_token(profile: str) -> str:
    _require_keyring()
    value = keyring.get_password("redcap-api-mcp/token", profile)
    if not value:
        raise ConfigurationError("No API token is stored for this profile. Run redcap-mcp setup.")
    return value


def set_token(profile: str, token: str) -> None:
    _require_keyring()
    keyring.set_password("redcap-api-mcp/token", profile, token)


def delete_token(profile: str) -> None:
    _require_keyring()
    try:
        keyring.delete_password("redcap-api-mcp/token", profile)
    except keyring.errors.PasswordDeleteError:
        pass


def pseudonym_key(profile: str) -> bytes:
    _require_keyring()
    value = keyring.get_password("redcap-api-mcp/pseudonym-key", profile)
    if not value:
        value = secrets.token_urlsafe(48)
        keyring.set_password("redcap-api-mcp/pseudonym-key", profile, value)
    return value.encode()
