import pytest

from redcap_mcp.config import ConfigStore
from redcap_mcp.errors import RedcapMcpError
from redcap_mcp.models import Profile
from redcap_mcp.service import RedcapService


class FakeClient:
    def __init__(self, profile, token):
        self.profile = profile

    async def export(self, content, **payload):
        if content == "metadata":
            return [
                {
                    "field_name": "record_id",
                    "field_type": "text",
                    "identifier": "y",
                    "field_label": "Record",
                },
                {"field_name": "age", "field_type": "text", "identifier": "", "field_label": "Age"},
            ]
        if content == "record":
            return [{"record_id": "1", "age": "20"}, {"record_id": "2", "age": ""}]
        if content == "report":
            return [{"record_id": "1", "age": "20", "mystery": "secret"}]
        return []


@pytest.fixture
def service(tmp_path, monkeypatch):
    store = ConfigStore(tmp_path / "config.json")
    store.put_profile(Profile("safe", "https://example.test", report_aliases={"ages": "5"}), True)
    monkeypatch.setattr("redcap_mcp.service.get_token", lambda _: "token")
    monkeypatch.setattr("redcap_mcp.service.pseudonym_key", lambda _: b"key")
    return RedcapService(store, FakeClient)


@pytest.mark.asyncio
async def test_report_unknown_columns_fail_closed(service):
    result = await service.run_report(None, "ages", "raw", False, 50)
    assert result["rows"] == [{"record_alias": result["rows"][0]["record_alias"], "age": "20"}]
    assert set(result["withheld_columns"]) == {"record_id", "mystery"}


@pytest.mark.asyncio
async def test_summary_and_limits(service):
    result = await service.summarize_records(None, ["age"], None, None, None, None, False)
    assert result["fields"]["age"] == {
        "missing": 1,
        "non_missing": 1,
        "distinct": 1,
        "sum": 20.0,
        "mean": 20.0,
        "min": 20.0,
        "max": 20.0,
    }
    with pytest.raises(RedcapMcpError):
        await service.query_records(None, ["age"], None, None, None, None, "raw", False, 201)


@pytest.mark.asyncio
async def test_query_requires_scope(service):
    with pytest.raises(RedcapMcpError):
        await service.query_records(None, None, None, None, None, None, "raw", False, 50)


@pytest.mark.asyncio
async def test_record_id_lookup_is_blocked_without_both_identifier_gates(service):
    with pytest.raises(Exception, match="protected field"):
        await service.query_records(None, ["age"], None, None, None, ["1"], "raw", False, 50)
