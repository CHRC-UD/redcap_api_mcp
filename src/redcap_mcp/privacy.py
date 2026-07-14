from __future__ import annotations

import hashlib
import hmac
from collections.abc import Iterable

from .errors import PrivacyError
from .models import Profile

SENSITIVE_SYSTEM_FIELDS = {"redcap_survey_identifier"}
SAFE_SYSTEM_FIELDS = {
    "redcap_event_name",
    "redcap_repeat_instrument",
    "redcap_repeat_instance",
    "redcap_data_access_group",
}


def metadata_map(metadata: Iterable[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row.get("field_name", ""): row for row in metadata if row.get("field_name")}


def protected_fields(profile: Profile, metadata: dict[str, dict[str, str]]) -> set[str]:
    marked = {name for name, row in metadata.items() if row.get("identifier", "").lower() == "y"}
    return marked | set(profile.protected_fields) | SENSITIVE_SYSTEM_FIELDS


def base_field(column: str, metadata: dict[str, dict[str, str]]) -> str:
    if column in metadata:
        return column
    # REDCap checkbox export columns are field___coded_value.
    for name, row in metadata.items():
        if row.get("field_type") == "checkbox" and column.startswith(name + "___"):
            return name
    return column


def identifiers_allowed(profile: Profile, requested: bool) -> bool:
    return requested and profile.identifiers_enabled


def assert_safe_inputs(
    fields: Iterable[str] | None,
    filters: Iterable[str] | None,
    group_by: Iterable[str] | None,
    profile: Profile,
    metadata: dict[str, dict[str, str]],
    include_identifiers: bool,
) -> None:
    if identifiers_allowed(profile, include_identifiers):
        return
    protected = protected_fields(profile, metadata)
    requested = list(fields or []) + list(filters or []) + list(group_by or [])
    bad = [name for name in requested if base_field(name, metadata) in protected]
    if bad:
        raise PrivacyError(
            "A protected field cannot be requested, filtered, or grouped without identifier access."
        )


def alias(value: object, key: bytes) -> str:
    digest = hmac.new(key, str(value).encode("utf-8"), hashlib.sha256).hexdigest()[:20]
    return "record_" + digest


def sanitize_rows(
    rows: list[dict[str, object]],
    profile: Profile,
    metadata: dict[str, dict[str, str]],
    include_identifiers: bool,
    pseudonym_key: bytes,
) -> tuple[list[dict[str, object]], list[str]]:
    if identifiers_allowed(profile, include_identifiers):
        return rows, []
    protected = protected_fields(profile, metadata)
    record_id = next(
        (
            name
            for name, row in metadata.items()
            if row.get("field_type") == "text"
            and row.get("field_name") == name
            and name in protected
        ),
        None,
    )
    withheld: set[str] = set()
    cleaned: list[dict[str, object]] = []
    for row in rows:
        safe: dict[str, object] = {}
        for column, value in row.items():
            base = base_field(column, metadata)
            if base in protected or (base not in metadata and column not in SAFE_SYSTEM_FIELDS):
                withheld.add(column)
                if column == record_id and value not in (None, ""):
                    safe["record_alias"] = alias(value, pseudonym_key)
                continue
            safe[column] = value
        cleaned.append(safe)
    return cleaned, sorted(withheld)
