from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from .audit import audit
from .client import RedcapClient
from .config import ConfigStore
from .errors import RedcapMcpError
from .privacy import assert_safe_inputs, identifiers_allowed, metadata_map, sanitize_rows
from .secrets import get_token, pseudonym_key

DEFAULT_LIMIT, HARD_LIMIT, MAX_FIELDS, MAX_OUTPUT, MAX_PROCESS = (
    50,
    200,
    100,
    1024 * 1024,
    100 * 1024 * 1024,
)


class RedcapService:
    def __init__(self, store: ConfigStore | None = None, client_factory=RedcapClient):
        self.store, self.client_factory = store or ConfigStore(), client_factory

    def _client(self, profile_name: str | None):
        profile = self.store.get_profile(profile_name)
        return profile, self.client_factory(profile, get_token(profile.name))

    async def metadata(self, profile_name: str | None):
        profile, client = self._client(profile_name)
        return profile, metadata_map(await client.export("metadata"))

    async def list_profiles(self) -> dict[str, Any]:
        config = self.store.load()
        return {
            "profiles": [
                self.store.get_profile(name).public(name == config.get("default_profile"))
                for name in config["profiles"]
            ]
        }

    async def get_project(self, profile_name: str | None) -> dict[str, Any]:
        profile, client = self._client(profile_name)
        # These exports are all non-data structural metadata.
        project = await client.project_info()
        metadata = await client.export("metadata")
        events = await client.export("event")
        arms = await client.export("arm")
        forms = sorted({r.get("form_name", "") for r in metadata if r.get("form_name")})
        return {
            "source": "REDCap API",
            "profile": profile.name,
            "project": project,
            "longitudinal": bool(events),
            "instruments": forms,
            "events": events,
            "arms": arms,
        }

    async def search_fields(
        self,
        profile_name: str | None,
        query: str | None = None,
        forms: list[str] | None = None,
        field_types: list[str] | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        profile, metadata = await self.metadata(profile_name)
        limit = self._limit(limit)
        needle = (query or "").lower()
        protected = {
            k for k, v in metadata.items() if v.get("identifier", "").lower() == "y"
        } | set(profile.protected_fields)
        result = []
        for name, row in metadata.items():
            if (
                needle
                and needle not in name.lower()
                and needle not in row.get("field_label", "").lower()
            ):
                continue
            if forms and row.get("form_name") not in forms:
                continue
            if field_types and row.get("field_type") not in field_types:
                continue
            result.append(
                {
                    "field_name": name,
                    "label": row.get("field_label", ""),
                    "type": row.get("field_type", ""),
                    "validation": row.get("text_validation_type_or_show_slider_number", ""),
                    "choices": row.get("select_choices_or_calculations", ""),
                    "form": row.get("form_name", ""),
                    "protected": name in protected,
                }
            )
        return {
            "source": "REDCap metadata",
            "profile": profile.name,
            "fields": result[:limit],
            "truncated": len(result) > limit,
        }

    async def query_records(
        self,
        profile_name: str | None,
        fields: list[str] | None,
        forms: list[str] | None,
        events: list[str] | None,
        filter_logic: str | None,
        record_ids: list[str] | None,
        value_format: str,
        include_identifiers: bool,
        limit: int,
    ) -> dict[str, Any]:
        if not fields and not forms:
            raise RedcapMcpError("Specify at least one field or form.")
        profile, metadata = await self.metadata(profile_name)
        self._validate_fields(fields or [], metadata)
        filter_names = re.findall(r"\[([^\]]+)\]", filter_logic or "")
        if record_ids:
            # REDCap's `records` parameter targets the project's record-id
            # field (the first data-dictionary field), so it needs the same
            # two identifier gates as an explicit protected field.
            assert_safe_inputs(
                [next(iter(metadata))], None, None, profile, metadata, include_identifiers
            )
        assert_safe_inputs(
            fields,
            list(record_ids or []) + filter_names,
            None,
            profile,
            metadata,
            include_identifiers,
        )
        _, client = self._client(profile.name)
        rows = await client.export(
            "record",
            fields=fields or [],
            forms=forms or [],
            events=events or [],
            filterLogic=filter_logic or "",
            records=record_ids or [],
            rawOrLabel=value_format,
        )
        return self._data_response(
            "redcap_query_records", profile, metadata, rows, include_identifiers, limit
        )

    async def run_report(
        self,
        profile_name: str | None,
        report: str,
        value_format: str,
        include_identifiers: bool,
        limit: int,
    ) -> dict[str, Any]:
        profile, metadata = await self.metadata(profile_name)
        report_id = profile.report_aliases.get(report, report)
        if not report_id.isdigit():
            raise RedcapMcpError("Report must be a numeric ID or a configured alias.")
        _, client = self._client(profile.name)
        rows = await client.export("report", report_id=report_id, rawOrLabel=value_format)
        return self._data_response(
            "redcap_run_report", profile, metadata, rows, include_identifiers, limit
        )

    async def summarize_records(
        self,
        profile_name: str | None,
        fields: list[str],
        forms: list[str] | None,
        events: list[str] | None,
        filter_logic: str | None,
        group_by: list[str] | None,
        include_identifiers: bool,
    ) -> dict[str, Any]:
        profile, metadata = await self.metadata(profile_name)
        groups = group_by or []
        if len(groups) > 2:
            raise RedcapMcpError("At most two grouping fields are supported.")
        self._validate_fields(fields + groups, metadata)
        filter_names = re.findall(r"\[([^\]]+)\]", filter_logic or "")
        assert_safe_inputs(fields, filter_names, groups, profile, metadata, include_identifiers)
        _, client = self._client(profile.name)
        rows = await client.export(
            "record",
            fields=sorted(set(fields + groups)),
            forms=forms or [],
            events=events or [],
            filterLogic=filter_logic or "",
        )
        return self._summary_response(
            profile, metadata, rows, fields, groups, include_identifiers, "redcap_summarize_records"
        )

    async def summarize_report(
        self,
        profile_name: str | None,
        report: str,
        fields: list[str],
        group_by: list[str] | None,
        include_identifiers: bool,
    ) -> dict[str, Any]:
        profile, metadata = await self.metadata(profile_name)
        groups = group_by or []
        if len(groups) > 2:
            raise RedcapMcpError("At most two grouping fields are supported.")
        self._validate_fields(fields + groups, metadata)
        assert_safe_inputs(fields, None, groups, profile, metadata, include_identifiers)
        report_id = profile.report_aliases.get(report, report)
        if not report_id.isdigit():
            raise RedcapMcpError("Report must be a numeric ID or a configured alias.")
        _, client = self._client(profile.name)
        rows = await client.export("report", report_id=report_id)
        return self._summary_response(
            profile, metadata, rows, fields, groups, include_identifiers, "redcap_summarize_report"
        )

    def _data_response(self, tool, profile, metadata, rows, include_identifiers, limit):
        limit = self._limit(limit)
        safe, withheld = sanitize_rows(
            rows, profile, metadata, include_identifiers, pseudonym_key(profile.name)
        )
        truncated = len(safe) > limit
        safe = safe[:limit]
        while len(json.dumps(safe).encode()) > MAX_OUTPUT and safe:
            safe.pop()
            truncated = True
        result = {
            "source": "REDCap API",
            "profile": profile.name,
            "rows": safe,
            "returned_rows": len(safe),
            "truncated": truncated,
            "withheld_columns": withheld,
            "privacy": {"identifiers_included": identifiers_allowed(profile, include_identifiers)},
        }
        if identifiers_allowed(profile, include_identifiers):
            result["warning"] = "Identified data is being sent to the MCP client/model."
        audit(
            tool,
            profile.name,
            len(safe),
            identifiers_allowed(profile, include_identifiers),
            truncated,
        )
        return result

    def _summary_response(self, profile, metadata, rows, fields, groups, include_identifiers, tool):
        raw_size = len(json.dumps(rows).encode())
        if raw_size > MAX_PROCESS:
            raise RedcapMcpError("Result is too large to summarize; narrow the request.")
        safe, withheld = sanitize_rows(
            rows, profile, metadata, include_identifiers, pseudonym_key(profile.name)
        )
        output: dict[str, Any] = {
            "source": "REDCap API",
            "profile": profile.name,
            "row_count": len(safe),
            "withheld_columns": withheld,
            "fields": {},
        }
        for field in fields:
            values = [r.get(field) for r in safe]
            present = [v for v in values if v not in (None, "")]
            numeric = [float(v) for v in present if _numeric(v)]
            stats: dict[str, Any] = {
                "missing": len(values) - len(present),
                "non_missing": len(present),
                "distinct": len({str(v) for v in present}),
            }
            if numeric:
                stats.update(
                    sum=sum(numeric),
                    mean=sum(numeric) / len(numeric),
                    min=min(numeric),
                    max=max(numeric),
                )
            output["fields"][field] = stats
        if groups:
            buckets = Counter(tuple(str(r.get(g, "")) for g in groups) for r in safe)
            ranked = buckets.most_common(100)
            output["groups"] = [
                {"values": dict(zip(groups, key)), "count": count} for key, count in ranked
            ]
            if len(buckets) > 100:
                output["other_count"] = sum(count for _, count in buckets.most_common()[100:])
        output["privacy"] = {
            "identifiers_included": identifiers_allowed(profile, include_identifiers)
        }
        audit(
            tool, profile.name, len(safe), identifiers_allowed(profile, include_identifiers), False
        )
        return output

    @staticmethod
    def _validate_fields(fields, metadata):
        if len(fields) > MAX_FIELDS:
            raise RedcapMcpError(f"At most {MAX_FIELDS} fields may be requested.")
        unknown = [f for f in fields if f not in metadata]
        if unknown:
            raise RedcapMcpError("One or more requested fields are not in REDCap metadata.")

    @staticmethod
    def _limit(limit):
        if not 1 <= limit <= HARD_LIMIT:
            raise RedcapMcpError(f"Limit must be between 1 and {HARD_LIMIT}.")
        return limit


def _numeric(value: object) -> bool:
    try:
        float(str(value))
        return True
    except (TypeError, ValueError):
        return False
