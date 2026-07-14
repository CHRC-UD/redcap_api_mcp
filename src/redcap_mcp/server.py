from __future__ import annotations

from .service import RedcapService


def create_server(service: RedcapService | None = None):
    """Create the stdio MCP server; imports lazily so CLI setup works without the SDK."""
    from mcp.server.fastmcp import FastMCP

    api = service or RedcapService()
    mcp = FastMCP("REDCap Read-Only API")

    @mcp.tool()
    async def redcap_list_profiles() -> dict:
        """List configured REDCap profiles without exposing API URLs or secrets."""
        return await api.list_profiles()

    @mcp.tool()
    async def redcap_get_project(profile: str | None = None) -> dict:
        """Return REDCap project structure, forms, events, and arms."""
        return await api.get_project(profile)

    @mcp.tool()
    async def redcap_search_fields(
        profile: str | None = None,
        query: str | None = None,
        forms: list[str] | None = None,
        field_types: list[str] | None = None,
        limit: int = 50,
    ) -> dict:
        """Search the data dictionary; no record values are returned."""
        return await api.search_fields(profile, query, forms, field_types, limit)

    @mcp.tool()
    async def redcap_query_records(
        profile: str | None = None,
        fields: list[str] | None = None,
        forms: list[str] | None = None,
        events: list[str] | None = None,
        filter_logic: str | None = None,
        record_ids: list[str] | None = None,
        value_format: str = "raw",
        include_identifiers: bool = False,
        limit: int = 50,
    ) -> dict:
        """Return a bounded, privacy-filtered preview of REDCap records."""
        return await api.query_records(
            profile,
            fields,
            forms,
            events,
            filter_logic,
            record_ids,
            value_format,
            include_identifiers,
            limit,
        )

    @mcp.tool()
    async def redcap_run_report(
        profile: str | None = None,
        report: str = "",
        value_format: str = "raw",
        include_identifiers: bool = False,
        limit: int = 50,
    ) -> dict:
        """Run a configured saved report by numeric report ID or friendly alias."""
        return await api.run_report(profile, report, value_format, include_identifiers, limit)

    @mcp.tool()
    async def redcap_summarize_records(
        profile: str | None = None,
        fields: list[str] | None = None,
        forms: list[str] | None = None,
        events: list[str] | None = None,
        filter_logic: str | None = None,
        group_by: list[str] | None = None,
        include_identifiers: bool = False,
    ) -> dict:
        """Compute local summary statistics from a bounded REDCap response."""
        return await api.summarize_records(
            profile, fields or [], forms, events, filter_logic, group_by, include_identifiers
        )

    @mcp.tool()
    async def redcap_summarize_report(
        profile: str | None = None,
        report: str = "",
        fields: list[str] | None = None,
        group_by: list[str] | None = None,
        include_identifiers: bool = False,
    ) -> dict:
        """Compute local summary statistics from a saved REDCap report."""
        return await api.summarize_report(
            profile, report, fields or [], group_by, include_identifiers
        )

    return mcp


def run_stdio() -> None:
    create_server().run(transport="stdio")
